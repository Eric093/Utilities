
- Install Rust sous Ubuntu:
  ```
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  rustup toolchain install stable
  ```
- Test:
  ```
  cargo new hello-world
  cd hello-world
  cargo run
  ```
# L'install avec cargo ne fonctionne pas, (pb libsmb..)
# Par contre, l'install avec le script du site d'origine fonctionne: 
```
curl --proto '=https' --tlsv1.2 -sSLf "https://git.io/JBhDb" | sh
```
