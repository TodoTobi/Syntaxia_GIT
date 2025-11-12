import cv2
import requests

def capturar_y_enviar():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cv2.imwrite("captura.jpg", frame)
    cap.release()

    with open("captura.jpg", "rb") as f:
        r = requests.post("http://localhost:5000/api/imagen", files={"imagen": f})
    print(r.text)

if __name__ == "__main__":
    capturar_y_enviar()