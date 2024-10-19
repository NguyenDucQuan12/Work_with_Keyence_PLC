import tkinter as tk
from get_data_from_plc import read_sensor_from_PLC
from tkinter import Label, Button
import cv2
from PIL import Image, ImageTk
import requests
import threading
from io import BytesIO

# Địa chỉ IP của máy chủ
license_plate_url_api = "http://192.168.0.100:8000/license_plate/detect"  # Thay thế bằng API của bạn
def display():
    print("chạy PLC")

def get_license_plate_from_frame(image):
    """
    Hàm gửi ảnh đến API để kiểm tra biển số xe
    """
    print("Chuyển hình ảnh lên server")

    # Chuyển frame (numpy array) thành định dạng JPEG trong bộ nhớ
    _, buffer = cv2.imencode('.png', image)

    # Chuyển buffer thành byte stream để gửi qua API
    image_file = BytesIO(buffer)

    # Tạo dữ liệu tệp để gửi với yêu cầu POST
    files = {'image': ('frame.jpg', image_file, 'image/jpeg')}  # 'frame.jpg' là tên tệp giả định, 'image/jpeg' là kiểu MIME

    # Gửi yêu cầu POST tới API với dữ liệu tệp hình ảnh
    response = requests.post(license_plate_url_api, files=files)

    # Kiểm tra và in ra kết quả trả về từ API
    if response.status_code == 200:
        is_license_plate = response.json().get("is_license_plate")
        license_plate = response.json().get("license_plate")
        return is_license_plate, license_plate
    else:
        is_license_plate = False
        Error_content = f"{response.status_code} : {response.text}"
        return is_license_plate, Error_content


class LicensePlateApp:
    def __init__(self, window, window_title, plc, video_source="rtsp://192.168.0.21:554/1/stream1/Profile1"):
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source

        # Mở video source (camera)
        self.vid = cv2.VideoCapture(self.video_source)

        # Kiểm tra xem camera có mở được không
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", self.video_source)

        # Đặt chiều rộng và chiều cao của video là 500x500
        self.width = 500
        self.height = 500

        # Tạo canvas Tkinter để hiển thị video
        self.canvas = tk.Canvas(window, width=self.width, height=self.height)
        self.canvas.grid(row=0, column=0, columnspan=2)  # Đặt trong grid với vị trí cụ thể

        # Tạo một frame bên dưới để chứa các nút
        self.control_frame = tk.Frame(window)
        self.control_frame.grid(row=1, column=0, columnspan=2, pady=10)

        # Nút kiểm tra biển số xe
        self.btn_check = Button(self.control_frame, text="Check License Plate", command=self.check_license_plate, width=20)
        self.btn_check.grid(row=0, column=0, padx=10, pady=5)

        # Nhãn để hiển thị kết quả biển số
        self.result_label = Label(self.control_frame, text="License Plate Result: ", font=("Arial", 12))
        self.result_label.grid(row=0, column=1, padx=10, pady=5)

        # Thêm nút đóng ứng dụng
        self.btn_quit = Button(self.control_frame, text="Quit", command=self.window.quit, width=20)
        self.btn_quit.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

        # Biến để lưu trữ frame hiện tại
        self.current_frame = None

        # Khởi tạo luồng đọc video
        self.running = True
        self.video_thread = threading.Thread(target=self.update_frame, daemon=True)
        self.video_thread.start()

        # Cập nhật giao diện định kỳ
        self.update_ui()
        plc.run_process_another_threading(self.check_license_plate)

        self.window.mainloop()

    def update_frame(self):
        """
        Hàm chạy trong luồng riêng để cập nhật frame liên tục từ video source.
        """
        while self.running:
            ret, frame = self.vid.read()
            if ret:
                # Resize frame để phù hợp với kích thước 500x500
                self.current_frame = cv2.resize(frame, (self.width, self.height))
            # time.sleep(0.03)  # Tạm dừng một chút để không làm quá tải CPU

    def update_ui(self):
        """
        Hàm cập nhật giao diện UI để hiển thị frame mới.
        """
        if self.current_frame is not None:
            # Chuyển đổi frame sang định dạng Image để hiển thị trên Tkinter
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)))

            # Hiển thị hình ảnh trên canvas
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        # Lặp lại sau 15ms để cập nhật giao diện
        self.window.after(15, self.update_ui)

    def check_license_plate(self):
        # Gửi frame hiện tại đến API và nhận kết quả
        if self.current_frame is not None:
            is_license_plate, result = get_license_plate_from_frame(self.current_frame)

            # Cập nhật nhãn với kết quả trả về từ API
            if is_license_plate:
                self.result_label.config(text=f"License Plate: {result}")
            else:
                self.result_label.config(text=f"Error: {result}")

    def __del__(self):
        # Dừng luồng khi ứng dụng đóng
        self.running = False
        if self.vid.isOpened():
            self.vid.release()


# Tạo cửa sổ Tkinter và chạy ứng dụng
if __name__ == "__main__":

    plc = read_sensor_from_PLC()
    root = tk.Tk()
    app = LicensePlateApp(root, "License Plate Detection App", plc= plc)
