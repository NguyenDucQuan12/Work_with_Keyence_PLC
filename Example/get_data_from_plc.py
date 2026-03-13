import pymcprotocol  #pip install pymcprotocol
import queue
import ipaddress
import requests  #pip install requests
import socket
import logging
import threading
import time
from datetime import datetime


logger = logging.getLogger(__name__)

class read_sensor_from_PLC():
    def __init__(self, PLC_IP = "169.254.254.222", PLC_PORT = 5000, SENSOR_ADDRESS = "TN0"  ) :

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
                # print(wordunits_values)
                # logger.debug(wordunits_values)

                if wordunits_values:
                    current_state = wordunits_values[0]
                    print(f"Nhận tín hiệu từ PLC: {current_state}")
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
                    logger.info("Bắt đầu thực hiện xử lý khi có tín hiệu")
                    function(event)
                    logger.info("Kết thúc quá trình xử lý")
                    
                except Exception as e:
                    # Khi có tham số exc_info thì nó sẽ hiển thị chi tiết lỗi xảy ra
                    logger.error(f"Hàm thực hiện khi có tín hiệu từ PLC có lỗi: {e}", exc_info=True)
                finally:
                    # logger.info("Hoàn thành xử lý nhiệm vụ khi có tín hiệu từ PLC")
                    self.event_queue.task_done()
            
            # Đặt quảng nghỉ 0.5s, trước khi kiểm tra lại các giá trị trong hàng đợi
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
        Ghi giá trị `new_value` vào thanh ghi có địa chỉ `address`  
        """
        self.mc.batchwrite_wordunits(headdevice=address, values=[new_value])

class connect_plc_via_socket():
    """
    Kết nối tới PLC Keyence bằng phương pháp socket  
    """
    def __init__(self, plc_ip, port = 8501):

        # Địa chỉ IP và port kết nối tới PLC
        self.plc_ip = plc_ip
        self.port = port

        # Biến xác nhận kết nối
        self.connected_plc = False

        # Biến lấy dữ liệu từ API
        self.get_api = True

        # Tạo khóa để bảo vệ quá trình ghi địa chỉ
        self.lock = threading.Lock()
        # Khóa bảo vệ việc lấy dữ liệu từ bộ nhớ cache 
        self.plc_info_lock = threading.Lock()

        # Tạo hàng đợi lưu trữ các giá trị đọc được từ PLC
        self.register_value_queue = queue.Queue()
        self.max_queue_size = 10  # Giới hạn số lượng trong hàng đợi

        # Biến lưu trữ giá trị từ api
        self.plc_info_cache = {
            "position": None,
            "operator": None,
            "product": None
        }

        # Biến lưu trữ trạng thái trước đó của thanh ghi
        self.previous_state = 0

    def is_valid_ip(self, ip):
        """
        Kiểm tra tính hợp lệ của địa chỉ IP
        """
        try:
            ipaddress.ip_address(ip)  # Kiểm tra cả IPv4 và IPv6
            return True
        except ValueError:
            return False

    def connect(self):
        """
        Kết nối tới PLC bằng Socket
        """
        try:
            # Kiểm tra địa chỉ IP trước khi kết nối
            if not self.is_valid_ip(self.plc_ip):
                logger.error(f"Địa chỉ IP '{self.plc_ip}' không hợp lệ.")

                return self.connected_plc

            # Tạo socket TCP/IP
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(10)  # Thiết lập thời gian chờ kết nối (timeout) là 10 giây

            # Kết nối tới PLC
            self.client.connect((self.plc_ip, self.port))
            # Tạo một luồng (stream) từ socket đã kết nối. 'rwb' nghĩa là read, write và binary
            self.stream = self.client.makefile('rwb')

            logger.debug(f"Đã kết nối tới PLC tại {self.plc_ip}:{self.port}")
            self.connected_plc = True

            return self.connected_plc

        except socket.timeout:
            logger.error(f"Lỗi kết nối: Quá thời gian chờ khi kết nối tới PLC tại {self.plc_ip}:{self.port}")
        except socket.error as e:
            logger.error(f"Lỗi socket khi kết nối tới PLC tại {self.plc_ip}:{self.port} - {e}")
        except Exception as e:
            logger.error(f"Lỗi không xác định khi kết nối tới PLC {self.plc_ip}: {e}")

        return self.connected_plc
    
    def disconnect(self):
        """
        Ngắt kết nối tới PLC
        """
        # Xác nhận ngắt kết nối
        self.connected_plc = False
        
        try:
            # Đóng các kết nối tới PLC
            if self.stream:
                self.stream.close()
                logger.debug("Đã đóng stream.")

            if self.client:
                self.client.close()
                logger.debug("Đã đóng kết nối socket.")

        except Exception as e:
            logger.error(f"Lỗi khi ngắt kết nối: {e}")

    def is_connected(self):
        """
        Kiểm tra kết nối hiện tại với PLC
        """
        try:
            self.client.send(b'')  # Gửi một byte rỗng để kiểm tra kết nối
            logger.info("Kết nối vẫn mở.")
            return True
        except socket.error as e:
            logger.error(f"Kết nối bị lỗi: {e}")
            return False
    
    def read_data(self, address):
        """
        Đọc dữ liệu từ PLC có địa chỉ là: `address`  
        Định dạng: `RD + dấu cách + địa chỉ thanh ghi + định dạng dữ liệu (nếu ko chỉ định sẽ lấy mặc định) + ngắt dòng (carriage return: CR)`  
        Một số địa chỉ đặc biệt:  
        - Timer: Đọc giá trị hiện tại là `T0 --> T3999` và cài đặt giá trị là `TS0 ---> TS3999`  
        - Counter: Đọc giá trị hiện tại là `C0 --> C3999` và cài đặt giá trị là `CS0 --> CS3999` 
        - File Register: `FM0 ---> FM32767` hoặc `ZF0 --> ZF524287`   

        Tài liệu tham khảo tại tệp PDF `User's Manual` của `Keyence` tại chapter 8: `HOST-LINK COMMUNICATION FUNCTION`  
        """
        # Trả về giá trị biểu thị lỗi
        error_value = -9999
        
        if not self.connected_plc:
            logger.error(f"Chưa kết nối tới PLC {self.plc_ip} để đọc giá trị {address}")
            return error_value
        
        # Lệnh + Dấu cách + Địa chỉ + ngắt dòng + xuống dòng mới
        command = f"RD {address}\r\n"
        
        try:
            # Thực hiện chuyển đổi câu lệnh từ chuỗi thành byte sử dụng mã hóa ascii và gửi câu lệnh tới PLC
            self.stream.write(command.encode('ascii'))
            # Gửi dữ liệu ngay lập tức mà không bị giữ lại trong bộ đệm
            self.stream.flush()
            
            # Đọc giá trị trả về từ PLC: 'xxx\r\n'
            response = self.stream.readline().decode('ascii')

            # Loại bỏ ký tự '\r' và '\n' bằng strip
            clean_value = response.strip()

            # Chuyển chuỗi đã làm sạch thành int, có một số thanh ghi có giá trị: '0,0000000050,0000000050' nên ko thể chuyển thẳng về int được
            # register_value_int = int(clean_value)

            return clean_value
        
        except Exception as e:
            logger.error(f"Lỗi khi đọc dữ liệu thanh ghi {address}: {e}")
            return error_value
    
    def write_data(self, address, value):
        """
        Thiết lập giá trị cho PLC  
        Định dạng: `WR + dấu cách + địa chỉ thanh ghi + định dạng dữ liệu (nếu ko chỉ định sẽ lấy mặc định) + ngắt dòng`  
        Một số địa chỉ đặc biệt:  
        - Timer: Đọc giá trị hiện tại là `T0 --> T3999` và cài đặt giá trị là `TS0 ---> TS3999`  
        - Counter: Đọc giá trị hiện tại là `C0 --> C3999` và cài đặt giá trị là `CS0 --> CS3999` 
        - File Register: `FM0 ---> FM32767` hoặc `ZF0 --> ZF524287`   

        Tài liệu tham khảo tại tệp PDF `User's Manual` của `Keyence` tại chapter 8: `HOST-LINK COMMUNICATION FUNCTION`  
        """
        # Trả về giá trị biểu thị lỗi
        error_value = False
        
        if not self.connected_plc:
            logger.error(f"Chưa kết nối tới PLC {self.plc_ip} để đọc giá trị {address}")
            return error_value
        
        # Câu lệnh viết giá trị vào thanh ghi
        command = f"WR {address} {value}\r\n"
        
        try:
            # Thực hiện chuyển đổi câu lệnh từ chuỗi thành byte sử dụng mã hóa ascii và gửi câu lệnh tới PLC
            self.stream.write(command.encode('ascii'))
            # Gửi dữ liệu ngay lập tức mà không bị giữ lại trong bộ đệm
            self.stream.flush()
            
            # Trả về kết quả ghi dữ liệu vào PLC
            response = self.stream.readline().decode('ascii')
            return response
        
        except Exception as e:
            logger.error(f"Lỗi khi ghi dữ liệu vào thanh ghi {address}: {e}")
            return error_value
        
    def update_sensor_address(self, new_address):
        """
        Thay đổi địa chỉ thanh ghi trong khi vẫn đang đọc dữ liệu
        """        
        with self.lock:
            self.register_address = new_address

        logger.info(f"Địa chỉ đọc thanh ghi đã được cập nhật: {self.register_address}")
    
    def read_data_plc_in_loop(self, address, time_break = 0.1, register_value_queue= None, plc_ip = None, plc_name = None):
        """
        Đọc giá trị từ địa chỉ thanh ghi với thời gian thực  
        Khoảng thời gian đọc cách nhau `time_break` để tránh tiêu tốn quá nhiều tài nguyên  
        Đơn vị thời gian là `ms`  
        """
        # Khởi tạo địa chỉ thanh ghi cần đọc liên tục và thời gian nghỉ giữa các lần đọc
        self.register_address = address
        self.time_break = time_break

        # Khởi tạo thread nhận dữ liệu từ API và cập nhật vào bộ nhớ cache
        self.plc_info_api_thread = threading.Thread(target=self.fetch_api_data, args=(None,), daemon=True)
        self.plc_info_api_thread.start()

        # Khởi tạo thread lắng nghe tín hiệu từ cảm biến, nếu có tín hiệu thì chuyển vào hàng đợi
        self.read_data_plc_thread = threading.Thread(target=self.read_data_plc_in_thread, args= (register_value_queue, plc_ip, plc_name), daemon= True)
        self.read_data_plc_thread.start()

    def read_data_plc_in_thread (self, register_value_queue, plc_ip, plc_name):
        """
        Đọc giá trị PLC trong 1 luồng   
        Chỉ sử dụng hàm cho các thanh ghi có 2 giá trị: `ON:1` và `OFF:0`  
        """    
        # Lấy vị trí lưu giá trị
        if not register_value_queue:
            register_value_queue = self.register_value_queue

        while self.connected_plc:         
            try:
                # Đảm bảo rằng không có sự thay đổi địa chỉ trong khi đọc tín hiệu
                with self.lock:
                    SENSOR_ADDRESS = self.register_address  # Lấy địa chỉ hiện tại an toàn
                    TIME_BREAK = self.time_break

                # Lấy giá trị tín hiệu từ địa chỉ trên
                register_value = self.read_data(address= SENSOR_ADDRESS)
                # print(f"Nhận tín hiệu từ PLC: {register_value}")
                register_value_int = int(register_value)

                # Kiểm tra sự thay đổi trạng thái, từ OFF sang ON, và thêm vào hàng đợi
                if register_value_int == 1 and self.previous_state == 0:

                    # print(f"Thiết bị tại thanh ghi đã được bật: {register_value}")
                    # logger.warning(f"Nhận tín hiệu từ PLC: {register_value}")

                    # Lấy dữ liệu API từ bộ nhớ cache
                    with self.plc_info_lock:
                        value_api = self.plc_info_cache

                    # Thêm thông tin nhận được từ PLC vào hàng đợi 
                    plc_info = {
                        "plc_ip": plc_ip,
                        "plc_name": plc_name,
                        "register_value": register_value_int,
                        "time": datetime.now()
                    }

                    plc_info.update(value_api)  # Kết hợp value_api vào plc_info

                    if register_value_queue.qsize() >= self.max_queue_size:
                        logger.warning("Số lượng tín hiệu tồn động chưa xử lý hết, không thể thêm vào hàng đợi")

                    else:
                        # logger.warning(f"Đưa thông tin nhận được từ PLC vào hàng đợi: {plc_info}")
                        register_value_queue.put(plc_info)

                # Cập nhật lại biến `self.previous_state` để so sánh lần tiếp theo
                self.previous_state = register_value_int

            except Exception as e:
                logger.error(f"Không thể đọc tín hiệu từ cảm biến: {e}")
                # Đưa giá trị lỗi vào hàng đợi khi không thể đọc tín hiệu từ cảm biến
                register_value_queue.put({
                        "plc_ip": plc_ip,
                        "plc_name": plc_name,
                        "register_value": -9999,  # Giá trị lỗi
                        "time": datetime.now(),
                        "position": None,
                        "operator": None,
                        "product": None
                    })

            # Đặt 1 quảng nghỉ giữa các lần đọc tín hiệu, bởi nếu ko có quảng nghỉ thì nó sẽ cố gắng đọc liên tục giá trị cảm biến nhanh nhất có thể, như vậy tiêu tốn nhiều CPU
            # Nếu thực sự cần đọc các giá trị gần như là chính xác từng mili giây thì mới đặt TIME_BREAK = 0
            time.sleep(TIME_BREAK)

    def get_value_register_address(self, address, time_break = 0.2):
        """
        Đọc 1 giá trị từ thanh ghi và trả về giá trị gốc của thanh ghi đó
        """
        # Khởi tạo địa chỉ thanh ghi cần đọc liên tục và thời gian nghỉ giữa các lần đọc
        self.register_address = address
        self.time_break = time_break

        # Khởi tạo thread lắng nghe tín hiệu từ cảm biến, nếu có tín hiệu thì chuyển vào hàng đợi
        self.get_value_plc_thread = threading.Thread(target=self.get_value_register_address_in_thread, daemon= True)
        self.get_value_plc_thread.start()

    def get_value_register_address_in_thread(self):
        """
        Đọc bất kỳ giá trị nào từ 1 thanh ghi cụ thể:  
        - Bit: `0 và 1`  
        - Decimal  
        - Hexa
        - Tuple   
        ...
        """
        while self.connected_plc:         
            try:
                # Đảm bảo rằng không có sự thay đổi địa chỉ trong khi đọc tín hiệu
                with self.lock:
                    SENSOR_ADDRESS = self.register_address  # Lấy địa chỉ hiện tại an toàn
                    TIME_BREAK = self.time_break

                # Lấy giá trị tín hiệu từ địa chỉ trên
                register_value = self.read_data(address= SENSOR_ADDRESS)
                # print(f"Nhận tín hiệu từ PLC: {register_value}")

                logger.warning(f"Nhận tín hiệu từ PLC: {register_value}")

                # if self.register_value_queue.qsize() >= self.max_queue_size:
                #     logger.warning("Số lượng tín hiệu tồn động chưa xử lý hết, không thể thêm vào hàng đợi")

                # else:
                #     logger.debug('Thêm dữ liệu vào hàng đợi xử lý: %s', register_value)
                #     self.register_value_queue.put(register_value)

            except Exception as e:
                logger.error(f"Không thể đọc tín hiệu từ cảm biến: {e}")
                # Đưa giá trị 3 vào hàng đợi khi không thể đọc tín hiệu từ cảm biến
                self.register_value_queue.put(-9999)

            # Đặt 1 quảng nghỉ giữa các lần đọc tín hiệu, bởi nếu ko có quảng nghỉ thì nó sẽ cố gắng đọc liên tục giá trị cảm biến nhanh nhất có thể, như vậy tiêu tốn nhiều CPU
            # Nếu thực sự cần đọc các giá trị gần như là chính xác từng mili giây thì mới đặt TIME_BREAK = 0
            time.sleep(TIME_BREAK)

    def process_events(self, function):
        """
        Sau khi tín hiệu được thêm vào hàng đợi, có nghĩa là đã sẵn sàng để xử lý  
        Tiến hành chạy hàm xử lý với các giá trị nhận được từ hàng đợi  
        """
        while self.connected_plc:
            # Kiểm tra nếu hàng đợi tồn tại giá trị thì mới bắt đầu lấy giá trị đó ra và xử lý
            if not self.register_value_queue.empty():
                event = self.register_value_queue.get(timeout=1)
                try:
                    # Nếu nhận tín hiệu có giá trị: -9999 thì là lỗi
                    if event["register_value"] == -9999:
                        self.connected_plc = False

                    logger.info("Bắt đầu thực hiện xử lý khi có tín hiệu")
                    function(event)
                    logger.info("Kết thúc quá trình xử lý")
                    
                except Exception as e:
                    # Khi có tham số exc_info thì nó sẽ hiển thị chi tiết lỗi xảy ra
                    logger.error(f"Hàm thực hiện khi có tín hiệu từ PLC có lỗi: {e}", exc_info=True)
                finally:
                    # logger.info("Hoàn thành xử lý nhiệm vụ khi có tín hiệu từ PLC")
                    self.register_value_queue.task_done()
            
            # Đặt quảng nghỉ 0.5s, trước khi kiểm tra lại các giá trị trong hàng đợi
            time.sleep(0.1)

    def fetch_api_data(self, url = None):
        """Lấy dữ liệu từ API và cập nhật vào bộ nhớ"""
        while self.get_api:
            try:
                # Kiểm tra URL có hợp lệ không
                if not url or not url.startswith("http://") or not url.startswith("https://"):
                    logger.error(f"URL '{url}' không hợp lệ.")
                    with self.plc_info_lock:
                        self.plc_info_cache = {
                            "position": None,
                            "operator": None,
                            "product": None
                        }
                    self.get_api = False
                    logger.info("Ngừng lấy dữ liệu từ API do URL không hợp lệ.")
                    return
                    # Không thưc hiện yêu cầu API nếu URL không hợp lệ
                    # time.sleep(3)  # Chờ 3s trước khi thử lại
                    # Bỏ qua vòng lặp này và tiếp tục vòng lặp tiếp theo
                    # continue
                
                # Gửi yêu cầu GET tới API
                response = requests.get(url=url)
                if response.status_code == 200:
                    data = response.json()

                    # Cập nhật các giá trị position, operator, product
                    with self.plc_info_lock:
                        self.plc_info_cache = {
                            "position": data["position"],
                            "operator": data["operator"],
                            "product": data["product"]
                        }
                    # logger.info("Dữ liệu từ API đã được cập nhật: %s", self.plc_info_cache)
                else:
                    logger.error("Không thể lấy dữ liệu từ API.")
            except Exception as e:
                logger.error(f"Đã xảy ra lỗi khi lấy dữ liệu từ API: {e}")
            
            # Thực hiện yêu cầu API mỗi 30-40 phút
            time.sleep(3)  # Chờ 3s


if __name__ == "__main__":

    """
    Thay các logger.xxx bằng print, bởi nó đang ghi log vào 1 file
    """
    def display(event):
        print(f"Có tín hiệu từ cảm biến gửi đến: {event}")
        
    # plc_reader = read_sensor_from_PLC()
    # plc_reader.write_sensor_address(new_value= 120, address= "TN0")
    # plc_reader.run_process_another_threading(function= display)

    plc_socket = connect_plc_via_socket(plc_ip="169.254.254.222")
    connected = plc_socket.connect()
    print(connected)
    plc_socket.read_data_plc_in_loop(address='M0', time_break= 0.1)
    # time_value = plc_socket.read_data(address="M0")
    # print(time_value)


    while True:
        time.sleep(1)
        # print("")
