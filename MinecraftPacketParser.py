import binascii
import re

def parse_hex_dump_line(line: str) -> bytes:
    cleaned = line.rstrip()
    if not cleaned.strip():
        return b""
    parts = cleaned.split(maxsplit=1)
    if len(parts) < 2:
        return b""
    content = parts[1]
    hex_zone = content[:48]
    hex_pairs = re.findall(r'[0-9a-fA-F]{2}', hex_zone)
    return binascii.unhexlify("".join(hex_pairs))

def read_var_int(data: bytes, offset: int = 0):
    value = 0
    position = 0
    current_index = offset
    
    while True:
        if current_index >= len(data):
            return None, 0  # not enough data
            
        current_byte = data[current_index]
        value |= (current_byte & 0x7F) << position
        
        if (current_byte & 0x80) == 0:
            break
            
        position += 7
        current_index += 1
        
        if position >= 35:
            raise ValueError("VarInt too big!")
            
    bytes_read = (current_index - offset) + 1
    return value, bytes_read

class MinecraftPacket:
    def __init__(self, from_client: bool, length: int, data: bytes):
        self.from_client = from_client
        self.length = length
        self.data = data

    def __str__(self):
        direction = "C -> S" if self.from_client else "S -> C"
        hex_preview = self.data[:16].hex().upper()
        if len(self.data) > 16:
            hex_preview += "..."
        return f"[{direction}] Packet size: {self.length} bytes | Data: {hex_preview}"

def parse_minecraft_dump(filename: str):
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    buffers = {
        True: bytearray(),# client buf
        False: bytearray()# server buf
    }
    
    packet_history = []

    def extract_packets_from_buffer(from_client: bool):
        buf = buffers[from_client]
        while True:
            if not buf:
                break
                
            packet_length, varint_size = read_var_int(buf, 0)
            
            if packet_length is None:
                break
                
            total_needed = varint_size + packet_length
            
            if len(buf) < total_needed:
                break
                
            packet_data = bytes(buf[varint_size:total_needed])
            
            packet = MinecraftPacket(from_client, packet_length, packet_data)
            packet_history.append(packet)
            
            del buf[:total_needed]

    for line in lines:
        if not line.strip():
            continue
            
        is_client = (line[0] != ' ')
        
        row_bytes = parse_hex_dump_line(line)
        if not row_bytes:
            continue
            
        buffers[is_client].extend(row_bytes)
        
        extract_packets_from_buffer(is_client)

    for is_client, buf in buffers.items():
        if buf:
            direction = "Client" if is_client else "Server"
            print(f"[Warn] Left {len(buf)} bytes in {direction} buffer")

    return packet_history


if __name__ == "__main__":
    dump_file = 'input.txt' 
    output_file = 'parsed_packets.txt'
    
    try:
        all_packets = parse_minecraft_dump(dump_file)
        
        with open(output_file, 'w', encoding='utf-8') as out:
            
            for idx, packet in enumerate(all_packets, start=1):
                direction = "CLIENT -> SERVER" if packet.from_client else "SERVER -> CLIENT"
                out.write(f"Packet #{idx:04d} | {direction} | Size: {packet.length} bytes\n")
                out.write("-" * 75 + "\n")
                
                bytes_per_line = 16
                for offset in range(0, len(packet.data), bytes_per_line):
                    chunk = packet.data[offset : offset + bytes_per_line]
                    
                    hex_string = " ".join(f"{b:02X}" for b in chunk)
                    hex_string = hex_string.ljust(bytes_per_line * 3 - 1)
                    
                    ascii_string = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                    
                    out.write(f"  [{offset:04X}]  {hex_string}  |  {ascii_string}\n")
                
                out.write("\n" + "=" * 75 + "\n\n")
                
        print(f"Sus saved to file: {output_file}")
            
    except FileNotFoundError:
        print(f"Can't open {dump_file}!")


