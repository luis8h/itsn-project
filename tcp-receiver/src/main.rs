use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, BufReader};
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let addr = "127.0.0.1:9000";
    let listener = TcpListener::bind(addr).await?;

    println!("🚀 Rust SOME/IP Receiver listening on {}", addr);

    loop {
        // Accept new connections in a loop
        let (socket, addr) = listener.accept().await?;
        println!("📡 Client connected: {}", addr);

        // Spawn a green thread (task) for each client
        tokio::spawn(async move {
            if let Err(e) = handle_client(socket).await {
                eprintln!("ℹ️ Client session ended: {}", e);
            }
        });
    }
}

async fn handle_client(mut stream: TcpStream) -> Result<(), Box<dyn Error>> {
    // Use a buffered reader for efficiency
    let mut reader = BufReader::new(&mut stream);
    let mut packet_buffer = [0u8; 2048];

    loop {
        // 1. Read the 4-byte length header
        let mut len_buf = [0u8; 4];
        // read_exact ensures we get all 4 bytes or returns an error
        reader.read_exact(&mut len_buf).await?;

        // Convert Big Endian bytes to u32
        let packet_len = u32::from_be_bytes(len_buf) as usize;

        if packet_len > packet_buffer.len() {
            return Err("Packet size exceeds buffer limit".into());
        }

        // 2. Read the actual Ethernet frame
        let frame = &mut packet_buffer[0..packet_len];
        reader.read_exact(frame).await?;

        // 3. Process the frame
        println!("✅ Received Frame | Length: {} bytes", packet_len);

        // Example: Print Destination MAC (first 6 bytes of Ethernet frame)
        if packet_len >= 6 {
            println!("   Dest MAC: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                frame[0], frame[1], frame[2], frame[3], frame[4], frame[5]);
        }
    }
}
