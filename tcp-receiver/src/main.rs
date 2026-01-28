use clap::Parser;
use pnet::datalink::{self, Channel, DataLinkReceiver, DataLinkSender, NetworkInterface};
use std::error::Error;
use std::sync::{Arc, Mutex};
use std::thread;
use tokio::io::{AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::broadcast;

// ------------------------------------------------------------------
// ARGUMENT PARSING STRUCT
// ------------------------------------------------------------------
use std::net::IpAddr;
#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    /// Name of the network interface (e.g., veth-carla)
    #[arg(short = 'i', long, default_value = "veth-carla")]
    interface: String,

    /// IP address to bind to (e.g., 127.0.0.1 or 0.0.0.0)
    #[arg(short = 'H', long, default_value = "127.0.0.1")]
    host: IpAddr,

    /// TCP port to listen on
    #[arg(short = 'p', long, default_value_t = 9000)]
    port: u16,
}


type BoxError = Box<dyn Error + Send + Sync>;

const MAX_PACKET_SIZE: usize = 4096;
const BROADCAST_QUEUE_SIZE: usize = 100;

// Main function -> entry point
#[tokio::main]
async fn main() -> Result<(), BoxError> {
    // Parse arguments from command line
    let args = Args::parse();
    let bind_addr = format!("{}:{}", args.host, args.port);

    println!("Starting Automotive Ethernet Bridge...");
    println!("Config Interface: {}", args.interface);
    println!("Config TCP Addr:  {}", bind_addr);

    // Use the parsed interface name
    let interface = find_interface(&args.interface)?;

    let (eth_tx, _) = broadcast::channel::<Vec<u8>>(BROADCAST_QUEUE_SIZE);

    let (tx_link, mut rx_link) = match datalink::channel(&interface, Default::default()) {
        Ok(Channel::Ethernet(tx, rx)) => (tx, rx),
        Ok(_) => return Err("Unhandled channel type (not Ethernet)".into()),
        Err(e) => return Err(format!("Failed to create datalink channel: {}", e).into()),
    };

    let eth_tx_clone = eth_tx.clone();

    // Spawn thread for pnet
    thread::spawn(move || {
        if let Err(e) = run_ethernet_ingress_loop(&mut *rx_link, eth_tx_clone) {
            eprintln!("Ethernet thread died: {}", e);
        }
    });

    let eth_sender = Arc::new(Mutex::new(tx_link));
    let listener = TcpListener::bind(&bind_addr).await?;

    println!("Bridge active on {}", bind_addr);

    loop {
        let (socket, addr) = listener.accept().await?;
        let eth_sender = eth_sender.clone();
        let eth_rx_subscriber = eth_tx.subscribe();

        tokio::spawn(async move {
            if let Err(e) = handle_client_session(socket, eth_sender, eth_rx_subscriber).await {
                eprintln!("Client {} disconnected: {}", addr, e);
            }
        });
    }
}

fn find_interface(name: &str) -> Result<NetworkInterface, BoxError> {
    datalink::interfaces()
        .into_iter()
        .find(|iface| iface.name == name)
        .ok_or_else(|| format!("Interface '{}' not found", name).into())
}

fn run_ethernet_ingress_loop(
    rx: &mut dyn DataLinkReceiver,
    broadcaster: broadcast::Sender<Vec<u8>>,
) -> Result<(), BoxError> {
    loop {
        match rx.next() {
            Ok(packet) => {
                let packet_vec = packet.to_vec();
                let _ = broadcaster.send(packet_vec);
            }
            Err(e) => {
                eprintln!("[!] Ethernet Read Error: {}", e);
            }
        }
    }
}

async fn handle_client_session(
    mut stream: TcpStream,
    eth_sender: Arc<Mutex<Box<dyn DataLinkSender>>>,
    mut eth_receiver: broadcast::Receiver<Vec<u8>>,
) -> Result<(), BoxError> {
    let addr = stream.peer_addr().unwrap_or_else(|_| "0.0.0.0:0".parse().unwrap());
    let (reader, mut writer) = stream.split();
    let mut buf_reader = BufReader::new(reader);

    loop {
        tokio::select! {
            result = async {
                let mut len_buf = [0u8; 4];
                buf_reader.read_exact(&mut len_buf).await?;
                let packet_len = u32::from_be_bytes(len_buf) as usize;

                if packet_len > MAX_PACKET_SIZE {
                    return Err(format!("Packet too large: {}", packet_len).into());
                }

                let mut buffer = vec![0u8; packet_len];
                buf_reader.read_exact(&mut buffer).await?;

                Ok::<Vec<u8>, BoxError>(buffer)
            } => {
                match result {
                    Ok(payload) => {
                        println!("[TCP -> ETH] Client {} sending {} bytes", addr, payload.len());
                        let mut tx = eth_sender.lock().unwrap();
                        tx.send_to(&payload, None);
                    }
                    Err(_) => {
                        println!("[i] Client {} closed TCP connection", addr);
                        return Ok(());
                    }
                }
            }
            recv_result = eth_receiver.recv() => {
                match recv_result {
                    Ok(packet) => {
                        println!("[ETH -> TCP] Forwarding {} bytes to client {}", packet.len(), addr);
                        let len_header = (packet.len() as u32).to_be_bytes();
                        if let Err(e) = writer.write_all(&len_header).await {
                             eprintln!("[!] TCP Write Error: {}", e);
                             return Err(e.into());
                        }
                        writer.write_all(&packet).await?;
                        writer.flush().await?;
                    }
                    Err(broadcast::error::RecvError::Lagged(count)) => {
                        eprintln!("[!] Client {} lagged: missed {} packets", addr, count);
                        continue;
                    }
                    Err(broadcast::error::RecvError::Closed) => return Ok(()),
                }
            }
        }
    }
}
