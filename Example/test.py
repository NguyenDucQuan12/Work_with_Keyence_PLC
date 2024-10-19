import pymcprotocol  #pip install pymcprotocol

# Địa chỉ IP của PLC KV-7500 và cổng TCP
PLC_IP = "192.168.0.111"  
PLC_PORT = 5000  

# Địa chỉ chứa giá trị cần đọc trên PLC Keyence trong KV-studio
SENSOR_ADDRESS = "M1000"  

# Biến lưu trữ trạng thái trước đó của cảm biến (giả sử bắt đầu là OFF)
previous_state = 0

# Khởi tạo kết nối MC Protocol
mc = pymcprotocol.Type3E()

# Kết nối tới PLC
mc.connect(PLC_IP, PLC_PORT)
print("Đã kết nối tới PLC")

def read_sensor_state(function):
    """
    Đọc tín hiệu từ cảm biến quang PR-G51N thông qua PLC KV-7500  
    Nếu không có tham số previous_state thì trong 1 giây PLC có thể gửi được 3-5 lần tín hiệu  
    Và như vậy chương trình sẽ phải xử lý 3-5 lần cho mỗi một giây
    """
    global previous_state
    try:
        #read M1000
        wordunits_values = mc.batchread_wordunits(headdevice=SENSOR_ADDRESS, readsize=1)

        if wordunits_values:
            current_state = wordunits_values[0]

            # Kiểm tra sự thay đổi trạng thái
            if current_state == 1 and previous_state == 0:
                # Nếu trạng thái thay đổi từ TẮT sang BẬT, gọi hàm càn làm việc
                function()

            # Cập nhật trạng thái trước đó để so sánh lần tiếp theo
            previous_state = current_state

    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":

    def do_somthing():
        print("Nhận được tín hiệu từ cảm biến")

    running = True
    while running:
        read_sensor_state(do_somthing)