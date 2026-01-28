## Getting Started

#### Install Dependencies
Install [cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html) for your operating system.

#### General Start
Run the app with root priveleges (for access to the ethernet interfaces):
```sh
cargo build
sudo ./target/debug/tcp-receiver
```
#### Test Setup Start
The test setup involves starting the application twice. For one of them another port and interface needs to be specified to avoid conflicts.

Compile:
```sh
cargo build
```

Start in the first terminal:
```sh
sudo ./target/debug/tcp-receiver
```

Start in the second terminal:
```sh
sudo ./target/debug/tcp-receiver -i veth-ecu -p 9001
```
