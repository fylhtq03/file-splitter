# File Splitter

A powerful Python-based tool for splitting large files into smaller parts and reassembling them with integrity verification and multi-threading support.

## Features

- 🔪 **Split large files** into manageable parts
- 🔗 **Reassemble parts** back into original files
- 🔒 **Integrity verification** with SHA-256 hashing
- ⚡ **Multi-threaded processing** for improved performance
- 💾 **Streaming processing** handles files of any size
- 🛡️ **Memory efficient** with configurable buffer sizes
- 📁 **Cross-platform** - works on Windows, Linux, and macOS

## Installation

### Pre-built Executable
Download the latest `file_splitter.exe` from the [Releases](https://github.com/fylhtq03/file-splitter/releases) page.

### From Source
```bash
git clone https://github.com/fylhtq03/file-splitter.git
cd file-splitter
python -m pip install -r requirements.txt
```

## Usage

### Basic Syntax
```bash
file_splitter.exe <command> [arguments]
```

### Splitting Files
```bash
file_splitter.exe split <file> <chunk_size> [options]
```

**Arguments:**
- `file` - Path to the file to split
- `chunk_size` - Size of each part in bytes

**Options:**
- `--verify-hash` - Calculate and verify file hash for integrity checking
- `--buffer-size` - Read/write buffer size in bytes (default: 8192)

**Examples:**
```bash
# Split file into 100MB parts
file_splitter.exe split large_file.iso 104857600

# Split with integrity verification and 64KB buffer
file_splitter.exe split big_database.zip 52428800 --verify-hash --buffer-size 65536
```

### Joining Files
```bash
file_splitter.exe join <parts_directory> [options]
```

**Arguments:**
- `parts_directory` - Directory containing file parts and .info file

**Options:**
- `-o, --output` - Output filename (default: original name)
- `-t, --threads` - Number of threads (0 = single-threaded, default: 0)
- `--buffer-size` - Read/write buffer size in bytes (default: 8192)

**Examples:**
```bash
# Join files single-threaded
file_splitter.exe join "large_file.iso_parts"

# Join with 4 threads and 32KB buffer
file_splitter.exe join "parts_folder" -t 4 --buffer-size 32768

# Join with custom output filename
file_splitter.exe join "parts_folder" -o "reconstructed_file.iso"
```

## Practical Examples

### Example 1: Splitting and Joining ISO Image
```bash
# Split ISO into 500MB parts with integrity check
file_splitter.exe split windows_install.iso 524288000 --verify-hash

# Reassemble with multi-threading
file_splitter.exe join "windows_install.iso_parts" -t 4
```

### Example 2: Working with Large Archives
```bash
# Split archive into 50MB parts
file_splitter.exe split huge_backup.rar 52428800

# Reassemble with large buffer for better performance
file_splitter.exe join "huge_backup.rar_parts" --buffer-size 131072
```

### Example 3: Performance Optimization

**For HDD (slower storage):**
```bash
file_splitter.exe join "parts_folder" -t 2 --buffer-size 32768
```

**For SSD (faster storage):**
```bash
file_splitter.exe join "parts_folder" -t 8 --buffer-size 65536
```

**For network drives:**
```bash
file_splitter.exe join "parts_folder" -t 1 --buffer-size 16384
```

## File Structure

When splitting files, the tool creates a directory structure:

```
original_file_parts/
├── original_file.part001
├── original_file.part002
├── ...
└── original_file.info
```

The `.info` file contains:
- Original filename
- Number of parts
- Original file size
- Chunk size
- SHA-256 hash (if verification enabled)

## Buffer Size Reference

Buffer sizes are specified in bytes. Common values:

| Size (bytes) | Description |
|--------------|-------------|
| 4096 | 4 KB - Conservative |
| 8192 | 8 KB - Default |
| 32768 | 32 KB - Balanced |
| 65536 | 64 KB - Fast |
| 131072 | 128 KB - High performance |
| 262144 | 256 KB - Maximum speed |

## Recommended Chunk Sizes

| Use Case | Recommended Size |
|----------|------------------|
| Network transfer | 10-100 MB |
| FAT32 storage | ≤ 4 GB |
| General purpose | 100-500 MB |
| Cloud storage | 50-200 MB |

## Troubleshooting

### Common Issues

**"File not found" error**
- Verify file path is correct
- Check file exists and is accessible

**"Part file not found" error**
- Ensure all parts are in the same directory
- Verify .info file is present

**Low performance**
- Reduce thread count for HDD
- Increase buffer size for SSD
- Close other resource-intensive applications

**Insufficient disk space**
- Ensure target drive has enough free space
- Free space needed = original file size

## Performance Tips

1. **Use multi-threading** for fast storage (SSD/NVMe)
2. **Increase buffer size** for better throughput
3. **Enable hash verification** for critical data
4. **Close background apps** during large operations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For help and support:
```bash
file_splitter.exe --help
file_splitter.exe split --help
file_splitter.exe join --help
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Current version: 1.0.0
```
