import pyaudio

def main():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("🎤 Danh sách các thiết bị Audio (Input/Output) trên hệ thống:")
    print("-" * 60)
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        name = device_info.get('name')
        max_input = device_info.get('maxInputChannels')
        max_output = device_info.get('maxOutputChannels')
        
        type_str = []
        if max_input > 0:
            type_str.append("Micro")
        if max_output > 0:
            type_str.append("Loa")
            
        print(f"Index {i}: {name} | [{', '.join(type_str)}]")
    print("-" * 60)
    p.terminate()

if __name__ == "__main__":
    main()
