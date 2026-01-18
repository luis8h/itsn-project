use pnet::datalink::{self, Channel, DataLinkSender};
use std::error::Error;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::io::AsyncWriteExt;
use tokio::io::{AsyncReadExt, BufReader};
use tokio::net::{TcpListener, TcpStream};

const USB_INTERFACE_NAME: &str = "veth-carla";

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let addr = "127.0.0.1:9000";

    // Find the network interface by name
    let interfaces = datalink::interfaces();
    let interface = interfaces
        .into_iter()
        .find(|iface| iface.name == USB_INTERFACE_NAME)
        .ok_or_else(|| format!("Could not find interface: {}", USB_INTERFACE_NAME))?;

    println!(
        "Found interface: {} (MAC: {:?})",
        interface.name, interface.mac
    );

    // Open a raw socket channel to the interface
    // NOTE: later use rx as a receiver for bidirectional messages
    let (mut tx, _rx) = match datalink::channel(&interface, Default::default()) {
        Ok(Channel::Ethernet(tx, rx)) => (tx, rx),
        Ok(_) => return Err("Unhandled channel type (not Ethernet)".into()),
        Err(e) => return Err(format!("Failed to create datalink channel: {}", e).into()),
    };

    // Wrap the sender in Arc<Mutex> so it can be shared across async tasks
    let packet_sender = Arc::new(Mutex::new(tx));

    // Start TCP Listener
    let listener = TcpListener::bind(addr).await?;
    println!("SOME/IP Receiver listening on {}", addr);
    println!("Forwarding targets to: {}", USB_INTERFACE_NAME);

    loop {
        let (socket, addr) = listener.accept().await?;
        println!("📡 Client connected: {}", addr);

        // Clone the sender handle for this specific task
        let sender_clone = packet_sender.clone();

        tokio::spawn(async move {
            if let Err(e) = handle_client(socket, sender_clone).await {
                eprintln!("ℹ️ Client session ended: {}", e);
            }
        });
    }
}

async fn handle_client(
    mut stream: TcpStream,
    sender: Arc<Mutex<Box<dyn DataLinkSender>>>,
) -> Result<(), Box<dyn Error>> {
    // 1. Split the TCP stream into a reader and a writer
    let (reader, mut writer) = stream.split();
    let mut buf_reader = BufReader::new(reader);

    println!("🔄 Bidirectional bridge established.");

    // 2. Run two tasks concurrently
    tokio::select! {
        // --- TASK 1: TCP -> Automotive Ethernet ---
        res = async {
            let mut packet_buffer = [0u8; 2048];
            println!("👀 Task 1: Waiting for data from TCP...");
            loop {
                let mut len_buf = [0u8; 4];
                buf_reader.read_exact(&mut len_buf).await?;
                let packet_len = u32::from_be_bytes(len_buf) as usize;
                println!("📏 Header received! Expecting {} bytes of payload.", packet_len); // <--- CHECK 2

                if packet_len > packet_buffer.len() {
                    return Err("Packet too large".into());
                }

                let frame_data = &mut packet_buffer[0..packet_len];
                buf_reader.read_exact(frame_data).await?;

                // --- ADD THIS PRINT BLOCK ---
                println!("📦 Forwarding Packet ({} bytes):", packet_len);
                // Prints as hex bytes: [00, AF, 12, ...]
                println!("{:02X?}", frame_data);
                // ----------------------------

                // Send to Hardware
                {
                    let mut tx = sender.lock().unwrap();
                    tx.send_to(frame_data, None);
                }
            }
            // Explicitly define the return type for this block
            #[allow(unreachable_code)]
            Ok::<(), Box<dyn Error>>(())
        } => res,

        // --- TASK 2: Dummy Data (or Hardware) -> TCP ---
        res = async {
            let mut interval = tokio::time::interval(Duration::from_secs(2));
            loop {
                interval.tick().await;

                let dummy_msg = b"STILL_ALIVE";
                let len_header = (dummy_msg.len() as u32).to_be_bytes();

                // Write [Length] + [Payload] back to the TCP Client
                writer.write_all(&len_header).await?;
                writer.write_all(dummy_msg).await?;
                writer.flush().await?;

                println!("📤 Dummy heartbeat sent to TCP client");
            }
            #[allow(unreachable_code)]
            Ok::<(), Box<dyn Error>>(())
        } => res,
    }
}
