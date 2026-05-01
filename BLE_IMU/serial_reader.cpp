/*
 *      Complile:
 *      g++ -O2 -std=c++17 -o serial_reader serial_reader.cpp

 * serial_reader.cpp
 * ------------------
 * Reads X,Y gyroscope lines from the Arduino Nano 33 BLE Sense over USB serial.
 * Parses each line and forwards as a compact UDP packet to localhost.
 *
 * Usage:
 *   ./serial_reader <serial_port> [udp_port]
 *
 * Examples:
 *   Linux/Mac:  ./serial_reader /dev/ttyACM0
 *
 * UDP packet format (12 bytes):
 *   [float x (4 bytes)][float y (4 bytes)][uint32_t seq (4 bytes)]
 *   seq = sequence number, increments each packet (lets Python detect drops)
 *
 * Compile:
 *   Linux/Mac: g++ -O2 -std=c++17 -o serial_reader serial_reader.cpp
 *   Windows:   g++ -O2 -std=c++17 -o serial_reader serial_reader.cpp -lws2_32
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <cstring>
#include <cstdint>
#include <csignal>
#include <atomic>

// ── Platform-specific serial + socket includes ────────────────────────────────
#ifdef _WIN32
  #include <windows.h>
  #include <winsock2.h>
  #pragma comment(lib, "ws2_32.lib")
  using socket_t = SOCKET;
  #define CLOSE_SOCKET(s) closesocket(s)
#else
  #include <fcntl.h>
  #include <termios.h>
  #include <unistd.h>
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  using socket_t = int;
  #define CLOSE_SOCKET(s) close(s)
  #define INVALID_SOCKET (-1)
#endif

// ── Config ────────────────────────────────────────────────────────────────────
static constexpr int    BAUD_RATE    = 115200;
static constexpr int    DEFAULT_PORT = 5005;
static constexpr char   UDP_HOST[]   = "127.0.0.1";
// ─────────────────────────────────────────────────────────────────────────────

// Graceful shutdown on Ctrl+C
static std::atomic<bool> g_running{true};
void handle_signal(int) { g_running = false; }

// ── UDP packet layout (packed, 12 bytes) ─────────────────────────────────────
#pragma pack(push, 1)
struct ImuPacket {
    float    x;
    float    y;
    uint32_t seq;
};
#pragma pack(pop)

// ── Serial port helpers ───────────────────────────────────────────────────────

#ifdef _WIN32

HANDLE open_serial(const std::string& port) {
    std::string full_port = "\\\\.\\" + port;
    HANDLE h = CreateFileA(full_port.c_str(), GENERIC_READ, 0, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        std::cerr << "[ERROR] Cannot open serial port: " << port << "\n";
        return INVALID_HANDLE_VALUE;
    }

    DCB dcb{};
    dcb.DCBlength = sizeof(dcb);
    GetCommState(h, &dcb);
    dcb.BaudRate = BAUD_RATE;
    dcb.ByteSize = 8;
    dcb.Parity   = NOPARITY;
    dcb.StopBits = ONESTOPBIT;
    SetCommState(h, &dcb);

    COMMTIMEOUTS timeouts{};
    timeouts.ReadIntervalTimeout         = 1;
    timeouts.ReadTotalTimeoutConstant    = 10;
    timeouts.ReadTotalTimeoutMultiplier  = 1;
    SetCommTimeouts(h, &timeouts);

    std::cerr << "[INFO] Opened " << port << " @ " << BAUD_RATE << " baud\n";
    return h;
}

// Read one newline-terminated line from the Windows serial handle
bool read_line(HANDLE h, std::string& out) {
    out.clear();
    char c;
    DWORD n;
    while (g_running) {
        if (!ReadFile(h, &c, 1, &n, nullptr) || n == 0) continue;
        if (c == '\n') return true;
        if (c != '\r') out += c;
    }
    return false;
}

#else

int open_serial(const std::string& port) {
    int fd = open(port.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0) {
        std::cerr << "[ERROR] Cannot open serial port: " << port << "\n";
        return -1;
    }

    struct termios tty{};
    tcgetattr(fd, &tty);

    // Set baud rate — 115200 requires a non-standard flag on Linux
    cfsetispeed(&tty, B115200);
    cfsetospeed(&tty, B115200);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;  // 8-bit chars
    tty.c_iflag &= ~IGNBRK;                        // disable break processing
    tty.c_lflag  = 0;                              // raw mode, no echo
    tty.c_oflag  = 0;                              // no remapping
    tty.c_cc[VMIN]  = 1;                           // block until 1 char read
    tty.c_cc[VTIME] = 0;                           // no read timeout
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);        // no flow control
    tty.c_cflag |= (CLOCAL | CREAD);               // enable receiver
    tty.c_cflag &= ~(PARENB | PARODD);             // no parity
    tty.c_cflag &= ~CSTOPB;                        // 1 stop bit
    tty.c_cflag &= ~CRTSCTS;                       // no hardware flow ctrl

    tcsetattr(fd, TCSANOW, &tty);

    std::cerr << "[INFO] Opened " << port << " @ " << BAUD_RATE << " baud\n";
    return fd;
}

// Read one newline-terminated line from the Linux/Mac file descriptor
bool read_line(int fd, std::string& out) {
    out.clear();
    char c;
    while (g_running) {
        ssize_t n = read(fd, &c, 1);
        if (n < 0) continue;
        if (n == 0) continue;
        if (c == '\n') return true;
        if (c != '\r') out += c;
    }
    return false;
}

#endif

// ── UDP socket setup ──────────────────────────────────────────────────────────

socket_t create_udp_socket(sockaddr_in& dest, int port) {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif

    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET) {
        std::cerr << "[ERROR] Failed to create UDP socket\n";
        return INVALID_SOCKET;
    }

    memset(&dest, 0, sizeof(dest));
    dest.sin_family      = AF_INET;
    dest.sin_port        = htons(port);
    dest.sin_addr.s_addr = inet_addr(UDP_HOST);

    std::cerr << "[INFO] UDP → " << UDP_HOST << ":" << port << "\n";
    return sock;
}

// ── Main ──────────────────────────────────────────────────────────────────────

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <serial_port> [udp_port]\n";
        std::cerr << "  e.g. " << argv[0] << " /dev/ttyACM0 5005\n";
        return 1;
    }

    std::string port     = argv[1];
    int         udp_port = (argc >= 3) ? std::stoi(argv[2]) : DEFAULT_PORT;

    std::signal(SIGINT,  handle_signal);
    std::signal(SIGTERM, handle_signal);

    // Open serial
#ifdef _WIN32
    HANDLE serial = open_serial(port);
    if (serial == INVALID_HANDLE_VALUE) return 1;
#else
    int serial = open_serial(port);
    if (serial < 0) return 1;
#endif

    // Open UDP socket
    sockaddr_in dest{};
    socket_t sock = create_udp_socket(dest, udp_port);
    if (sock == INVALID_SOCKET) return 1;

    std::cerr << "[INFO] Streaming — press Ctrl+C to stop\n";

    uint32_t seq       = 0;
    uint64_t sent      = 0;
    uint64_t skipped   = 0;
    std::string line;

    while (g_running) {
        if (!read_line(serial, line)) break;
        if (line.empty())       continue;
        if (line[0] == '#')     { std::cerr << "[META] " << line << "\n"; continue; }

        // Parse "X,Y"
        float x, y;
        char  comma;
        std::istringstream ss(line);
        if (!(ss >> x >> comma >> y) || comma != ',') {
            skipped++;
            continue;
        }

        // Pack and send
        ImuPacket pkt{x, y, seq++};
        sendto(sock, reinterpret_cast<const char*>(&pkt), sizeof(pkt), 0,
               reinterpret_cast<sockaddr*>(&dest), sizeof(dest));
        sent++;

        // Progress every 500 packets (~4 seconds at 119 Hz)
        if (sent % 500 == 0) {
            std::cerr << "[INFO] Sent " << sent << " packets  skipped " << skipped << "\n";
        }
    }

    std::cerr << "[INFO] Shutting down. Total sent: " << sent << "\n";
    CLOSE_SOCKET(sock);
#ifdef _WIN32
    CloseHandle(serial);
    WSACleanup();
#else
    close(serial);
#endif
    return 0;
}
