use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, BufReader};
use std::error::Error;
use std::sync::{Arc, Mutex};
use pnet::datalink::{self, Channel, DataLinkSender};

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

    println!("Found interface: {} (MAC: {:?})", interface.name, interface.mac);

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
    sender: Arc<Mutex<Box<dyn DataLinkSender>>>
) -> Result<(), Box<dyn Error>> {
    let mut reader = BufReader::new(&mut stream);
    // Buffer for the incoming TCP stream data
    let mut packet_buffer = [0u8; 2048];

    loop {
        // 1. Read the 4-byte length header
        let mut len_buf = [0u8; 4];
        reader.read_exact(&mut len_buf).await?;

        let packet_len = u32::from_be_bytes(len_buf) as usize;

        if packet_len > packet_buffer.len() {
            return Err("Packet size exceeds buffer limit".into());
        }

        let frame_data = &mut packet_buffer[0..packet_len];
        reader.read_exact(frame_data).await?;

        // Assuming 'frame_data' contains the full Ethernet header + Payload
        // TODO: maybe add a check here (might affect performance)
        if packet_len >= 14 { // Minimum Ethernet frame size
             println!("Received Frame | Length: {} bytes | Dest MAC: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                packet_len,
                frame_data[0], frame_data[1], frame_data[2], frame_data[3], frame_data[4], frame_data[5]
            );

            // NOTE: pnet operations are blocking
            {
                let mut tx = sender.lock().unwrap();

                tx.build_and_send(1, packet_len, &mut |new_packet| {
                    new_packet.copy_from_slice(frame_data);
                });
            }
            // ---------------------------------------------
        }
    }
}
