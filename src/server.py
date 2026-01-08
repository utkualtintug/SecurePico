import network
import socket
import time
import config
import shared

wlan = network.WLAN(network.STA_IF) # Init Wi-Fi interface

def connect_wifi():
    wlan.active(True) # Turn Wi-Fi on
    wlan.connect(config.SSID, config.PASSWORD)
    print("Connecting...")
    while not wlan.isconnected(): # Wait for connection
        time.sleep(1)
    print("IP:", wlan.ifconfig()[0])

def generate_html_response():
    html = """<!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>SecurePico</title>
        <script>
            function update() {
                fetch('/status')
                    .then(r => r.text())
                    .then(s => {
                        document.getElementById('stat').innerText = s;
                        // Change bg color based on status
                        document.body.style.backgroundColor = (s === 'ACTIVE') ? 'red' : 'white';
                    })
                    .catch(e => console.log(e));
            }
            setInterval(update, 2000);
            window.onload = update;
        </script>
    </head>
    <body style="text-align: center; font-family: sans-serif; padding-top: 50px;">
        <h1>Alarm Status:</h1>
        <h1 id="stat" style="font-size: 4em; margin: 20px 0;">LOADING...</h1>
    </body>
    </html>
    """
    return html

def start():
    connect_wifi()
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket() # Create socet
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow port reuse
    s.bind(addr) # Connected socet to address
    s.listen(1)
    print("Server ready")
    print("Web server started at: http://{}".format(wlan.ifconfig()[0]))

    while True:
        try:
            client, addr = s.accept()
            request = client.recv(1024) # 1024(byte) is buffer size. 
            req_str = str(request)

            if '/status' in req_str:
                status = "ACTIVE" if shared.alarm_active else "INACTIVE"
                client.send("HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n" + status)
            
            else:
                response = generate_html_response()
                client.send("HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n" + response)
            
            client.close()
        except Exception as e:
            print("Error:", e)