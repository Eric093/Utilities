
- Install Rust sous Ubuntu:
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  rustup toolchain install stable
- Test:
  cargo new hello-world
  cd hello-world
  cargo run
