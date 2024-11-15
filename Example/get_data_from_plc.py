import pymcprotocol  #pip install pymcprotocol
import queue
import logging
import threading
import time


logger = logging.getLogger(__name__)

class read_sensor_from_PLC():
    def __init__(self, PLC_IP = "192.168.0.10", PLC_PORT = 5000, SENSOR_ADDRESS = "M1000"  ) :

        """
        Class này nhận `IP PLC`, `Port PLC` và `địa chỉ thanh ghi` cần đọc tín hiệu từ PLC  
        Class này nhận tín hiệu từ `PLC` thông qua phương thức `MC` của `Mitsubusi` gọi là `MC Protocol`  
        """
        
        # Địa chỉ chứa giá trị cần đọc trên PLC Keyence trong KV-studio
        self.SENSOR_ADDRESS = SENSOR_ADDRESS

        # Tạo khóa để bảo vệ quá trình ghi địa chỉ
        self.lock = threading.Lock()

        # Khởi tạo kết nối MC Protocol
        self.mc = pymcprotocol.Type3E()

        # Kết nối tới PLC, xử lý ngoại lệ khi không thể kết nối
        try:
            self.mc.connect(PLC_IP, PLC_PORT)
            logger.debug("Đã kết nối tới PLC")
            self.connected = True
        except Exception as e:
            logger.error(f"Không thể kết nối tới PLC: {e}")
            self.connected = False

        # Biến lưu trữ trạng thái trước đó của cảm biến (giả sử bắt đầu là OFF) và tạo hàng đợi
        self.previous_state = 0
        self.event_queue = queue.Queue()
        self.max_queue_size = 4  # Giới hạn số lượng trong hàng đợi

        # Khởi tạo thread lắng nghe tín hiệu từ cảm biến, nếu có tín hiệu thì chuyển vào hàng đợi
        self.thread = threading.Thread(target=self.read_sensor_state)
        self.thread.daemon = True
        self.thread.start()

        # Không khởi tạo `process_events` ở đây mà sẽ khởi tạo sau khi function đã khởi tạo thành công
        # Bởi nếu thread này chạy mà function chưa được tạo thì sẽ gây ra lỗi
        self.processing_thread = None

    def run_process_another_threading(self, function):
        # Khởi tạo luồng xử lý sau khi nhận được tín hiệu từ cảm biến
        self.processing_thread = threading.Thread(target=self.process_events, args=(function,))
        self.processing_thread.daemon = True  # Đảm bảo luồng sẽ tự động kết thúc khi chương trình chính kết thúc
        self.processing_thread.start()

    def read_sensor_state(self):
        """
        Đọc tín hiệu từ cảm biến quang PR-G51N thông qua PLC KV-8000  
        Tín hiệu sẽ được lưu ở địa chỉ `SENSOR_ADDRESS` khi lập trình PLC  
        Nếu không có tham số `previous_state` thì trong 1 giây PLC có thể gửi tới 3-5 lần tín hiệu. Và như vậy chương trình sẽ phải xử lý 3-5 lần cho mỗi một giây  
        Sau khi nhận được tín hiệu từ PLC thì sẽ thêm tín hiệu đó vào hàng đợi `event_queue` để xử lý lần lượt  
        """
        while self.connected:         
            try:
                # Đảm bảo rằng không có sự thay đổi địa chỉ trong khi đọc tín hiệu
                with self.lock:
                    SENSOR_ADDRESS = self.SENSOR_ADDRESS  # Lấy địa chỉ hiện tại an toàn

                # Lấy giá trị tín hiệu từ địa chỉ trên
                wordunits_values =self.mc.batchread_wordunits(headdevice=SENSOR_ADDRESS, readsize=1)
                # logger.debug(wordunits_values)

                if wordunits_values:
                    current_state = wordunits_values[0]
                    logger.debug(f"Nhận tín hiệu từ PLC: {current_state}")
                    # print(f"Nhận tín hiệu từ PLC: {wordunits_values}")

                    # Kiểm tra sự thay đổi trạng thái, từ OFF sang ON, và thêm vào hàng đợi
                    if current_state == 1 and self.previous_state == 0:

                        if self.event_queue.qsize() >= self.max_queue_size:
                            logger.warning("Số lượng tín hiệu tồn động chưa xử lý hết, không thể thêm vào hàng đợi")
                        else:
                            logger.debug('Thêm dữ liệu vào hàng đợi xử lý: %s', current_state)
                            self.event_queue.put(current_state)

                    # Cập nhật lại biến `self.previous_state` để so sánh lần tiếp theo
                    self.previous_state = current_state

            except Exception as e:
                logger.error(f"Không thể đọc tín hiệu từ cảm biến: {e}")
                # Đưa giá trị 3 vào hàng đợi khi không thể đọc tín hiệu từ cảm biến
                self.event_queue.put(3)
            # Đặt 1 quảng nghỉ giữa các lần đọc tín hiệu, giảm đáng kể tiêu thụ CPU, bởi nếu ko có quảng nghỉ thì nó sẽ cố gắng đọc liên tục giá trị cảm biến nhanh nhất có thể, như vậy tiêu tốn nhiều CPU
            time.sleep(0.5)

    # Hàm này xử lý sự kiện sau khi nhận được tín hiệu từ PLC
    def process_events(self, function):
        """
        Sau khi tín hiệu được thêm vào hàng đợi, có nghĩa là đã sẵn sàng để xử lý  
        Tiến hành chạy hàm xử lý với các giá trị nhận được từ hàng đợi  
        """
        while self.connected:
            # Kiểm tra nếu hàng đợi tồn tại giá trị thì mới bắt đầu lấy giá trị đó ra và xử lý
            if not self.event_queue.empty():
                event = self.event_queue.get(timeout=1)
                try:
                    # Chạy hàm mà mong muốn xử lý khi có tín hiệu từ PLC
                    if event == 3:
                        self.connected = False
                    logger.info("Bắt đầu thực hiện quá trình cho một người")
                    function(event)
                    logger.info("Kết thúc quá trình cho một người")
                    
                except Exception as e:
                    # Khi có tham số exc_info thì nó sẽ hiển thị chi tiết lỗi xảy ra
                    logger.error(f"Hàm thực hiện khi có tín hiệu từ PLC có lỗi: {e}", exc_info=True)
                finally:
                    # logger.info("Hoàn thành xử lý nhiệm vụ khi có tín hiệu từ PLC")
                    self.event_queue.task_done()
            
            # Đặt quảng nghỉ 0.5s sau trước khi kiểm tra lại các giá trị trong hàng đợi
            time.sleep(0.5)

    def update_sensor_address(self, new_address):
        """
        Dùng để đọc dữ liệu từ 1 thanh ghi khác  
        Hàm này cho phép thay đổi địa chỉ thanh ghi cảm biến một cách an toàn  
        """        
        with self.lock:
            self.SENSOR_ADDRESS = new_address

        logger.info(f"Địa chỉ đọc thanh ghi đã được cập nhật: {self.SENSOR_ADDRESS}")

    def write_sensor_address(self, new_value, address):
        """
        Ghi giá trị `new_value` vào thành ghi có địa chỉ `address`  
        """
        self.mc.batchwrite_wordunits(headdevice=address, values=[new_value])

if __name__ == "__main__":

    """
    Thay các logger.xxx bằng print, bởi nó đang ghi log vào 1 file
    """
    def display(event):
        print(f"Có tín hiệu từ cảm biến gửi đến: {event}")
        
    plc_reader = read_sensor_from_PLC()
    plc_reader.run_process_another_threading(function= display)

    while True:
        time.sleep(1)
        # print("")
