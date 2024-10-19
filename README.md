# Work_with_Keyence_PLC
# Cách cấu hình PLC để có thể nhận tín hiệu cảm biến với python



# Mục lục

[I. Cài đặt Kv studio](#i-cài-đặt-kv-studio)
- [1. Chạy file setup](#1-chạy-file-setup)
- [2. Chạy file cập nhật](#2-chạy-file-cập-nhật)

[II. Cách sử dụng](#ii-cách-sử-dụng)
- [1. Kết nối PLC với Kv studio](#1-Kết-nối-PLC-với-Kv-studio)
  - [1. Kết nối bằng cáp USB-A](#1-Kết-nối-bằng-usb---a)
  - [2. Kết nối bằng ethernet](#2-Kết-nối-bằng-ethernet)
  - [3. Lập trình PLC](#3-Lập-trình-PLC)
- [2. Kết nối PLC với python thông qua MC protocol](#2-Kết-nối-PLC-với-python-thông-qua-MC-protocol)

[III. Ví dụ](#iii-Ví-dụ)


# I. Cài đặt Kv studio

## 1. Chạy file setup

Để cài đặt phần mềm **kv-studio** ta cần có file setup từ nhà cung cấp.  
Đầu tiên vào thư mục [kv_studio_setup](./kv_studio_setup/setup.exe) để tải **file setup** về và cài đặt  

![Chạy file setup kv studio](image/setup_kv_studio_file.png)

## 2. Chạy file cập nhật

Sau khi đã chạy file setup thì vào thư mục [kv_studio_setup](./kv_studio_setup/KVS_Update_G_1167.zip) **tải về toàn bộ file zip**, giải nén và chạy file cập nhật lên phiên bản **kv studio version 11.6** hoặc có thể sử dụng [kv_studio_setup](./kv_studio_setup/KV%20STUDIO%20Ver.6E.msi) để cập nhật **kv studio version 6.1**  

![file cập nhật phiên bản kv studio](image/update_kv_studio_file.png)

# II. Cách sử dụng

## 1. Kết nối PLC với Kv studio

Đây là bộ PLC demo, bào gồm **Nguồn 24V, PLC kv-7500, Kv-C32XC, Kv-C32TC**  

![Bộ PLC](image/Full_PLC.JPG)

### 1. Kết nối bằng cáp USB-A

Kết nối PLc với phần mềm **Kv Studio** có thể dùng cáp **USB-A**, đây cũng là phương pháp nhanh và tối ưu nhất  

![Cáp usb-a](image/USB-A-B.JPG)

Cắm 1 đầu usa vào PLC và đầu còn lại cắm vào máy tính  

![kết nối plc với phần mềm bằng cáp usb-a](image/USB_PLC.JPG)

Sau đó mở phần mềm **Kv-Studio**  

![kv studio version 11 6](image/kv_studio_v_116.png)

Chọn phương thức kết nối là **USB** và nhấn **Ctrl + F5** hoặc biểu tượng như bên dưới  

![chọn phương thức kết nối](image/connect_plc_via_usb.png)

### 2. Kết nối bằng ethernet

Còn một cách kết nối khác là sử dụng ethernet. Một đầu ethernet sẽ căm vào cổng ethernet nằm trên PLC, đầu ethernet còn lại cắm vào switch (dành cho nhiều thiết bị, thì các thiết bị cắm vào switch, vào 1 đầu máy tính cắm vào switch) hoặc cắm trực tiếp vào máy tính.  

![chọn phương thức kết nối](image/ethernet_plc.JPG)

Sau khi cắm xong thì cũng vào phần mềm kv studio và chọn phương thức kết nối là **ethernet** xong chọn **Read from PLC**  

![Kết nối bằng Ethernet](image/Connect_PLC_via_ethernet.png)

Sau đó nó sẽ hiển thị bảng lựa chọn thì ấn vào **Select all(S)** và chọn **Excute(E)** để kết nối với PLC  

![lựa chọn các thông số connect](image/Select_option_connect.png)

Đợi một lúc để tải các thông số từ PLC lên phần mềm, sau một lúc thì đây sẽ là giao diện nếu kết nối thành công:  

![Giao diện khi kết nối thành công](image/theme_when_connected.png)

Ta có thể thấy phía bảng bên trái sẽ là các thiết bị đang kết nối với PLC, Bộ PLC của tôi sẽ có hai khối mở rộng là Kv-C32XC, Kv-C32TC nên nó đang hiển thị đúng, và nếu nó hiển thị đúng thì các khối mở rộng và PLC sẽ có màu xanh , program: sẽ là các đoạn code PLC  

![Nếu PLC chưa tương thích](image/Full_PLC2.JPG)

Nếu PLC không hiển thị đúng với những thiết bị đang kết nối, thì các màu sắc sẽ là màu đỏ, và khi đó ta cần cấu hình cho nó kết nối khớp. Để PLC có thể nhận diện được các khối mở rộng thì ta vào chế độ **Editor** và click vào **Kv-7500**

![PLC lỗi không tìm được các khối mở rộng](image/PLC_error1.JPG)

Điều này có nghĩa là bộ PLC của chúng ta có 1 PLC và 2 khối mở rộng, nhưng phần mềm lại không nhận diện được, nên sẽ xảy ra lỗi  

![Thiếu bộ mở rộng](image/miss_open_device.png)  

Để sửa lỗi này thì ta quay lại chế độ **Editor** và nhấn vào tên bộ PLC ở mục ** Unit configuration**  

![mở chế dộ chỉnh sửa](image/open_unit_editor.png)

Từ bảng **unit editor** ta bấm vào **select unit** và chọn các thiết bị mà bạn đang kết nối với PLC:  

![Chọn các thiết bị tương ứng](image/chose_open_device.png)

Đây sẽ là kết quả cuối cùng:, mình có PLC kv-7500 tiếp theo kết nối đến Kv-C32XC, tiếp theo kết nối đến Kv-C32TC thì cũng phải chọn thiết bị mở rộng tương ứng. Và ấn **apply sau đó chọn OK**.    

![Apply các thiết bị](image/apply_open_device.png)

Bước cuối cùng là nạp chương trình này vào PLC để PLC ghi nhớ bằng cách nhấn ** Transfer to PLC**  
![alt text](image/transfer_to_plc.png)

Lưu ý: Nếu trong PLC đã có chương trình code, thì phải quan sát xem code đó có dòng nào màu đỏ không, nếu nó màu đỏ tức là chương trình đang lỗi, nên nạp code vào plc sẽ không chấp nhận, vì vậy hãy sửa code cho đúng hoặc xóa file code đi rồi nạp chương trình vào plc