# ------------------------------SERVER SOCKET---------------------------------

# Sources
# https://docs.python.org/3/howto/sockets.html
# https://docs.python.org/3/library/socket.html
# https://pythontic.com/modules/socket/accept
# https://pythontic.com/modules/socket/listen
# https://www.geeksforgeeks.org/file-flush-method-in-python/
# https://www.geeksforgeeks.org/socket-programming-python/
# https://pythontic.com/modules/socket/send


import socket
import sys
import datetime


def server_set_up(port_num_s):
    """Creates the server socket."""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind socket to port number and localhost
        localhost = '127.0.0.1'
        server_socket.bind((localhost, port_num_s))
        # call listen on socket, accepts up to 5 connections
        server_socket.listen(5)
        return server_socket
    except Exception as e:
        print(e)


def check_cmd_args():
    """Checks the port number is between 1024 and 64000 and there is only one
    argument passed to the server."""
    try:
        # read port number from command line
        port_num_s = int(sys.argv[1])
        if len(sys.argv) > 2:
            raise Exception("Error: Too many arguments, only one port number is permitted")
        if port_num_s < 1024 or port_num_s > 64000:
            raise ValueError("Error: Please choose a port number between 1024 and 64000")
    except Exception as e:
        print(e)
    else:
        return port_num_s


def recv_bytes(server_socket, client_socket):
    """Receives data from the client socket and checks it is not zero."""
    try:
        server_socket.settimeout(1)
        bytes_recv = client_socket.recv(4096)
        server_socket.settimeout(None)
        if len(bytes_recv) == 0:
            raise Exception("Error: No data received from client")
    except Exception as e:
        print(e)
    else:
        return bytes_recv


def process_recv_bytes(bytes_recv):
    """Processes the byte array sent by the client."""
    fixed_header = bytes_recv[:5]
    magic_no = int.from_bytes(fixed_header[0:2], 'big')
    send_type = int.from_bytes(fixed_header[2:3], 'big')
    file_name_len = int.from_bytes(fixed_header[3:5], 'big')
    file_name = bytes_recv[5:]
    return magic_no, send_type, file_name_len, file_name


def check_header(magic_no, send_type, file_name_len, file_name):
    """Checks that the bytearray received from the client has a header of the correct format."""
    header_correct = False
    file_corrupted = False
    try:
        if (magic_no == 0x497E) and (send_type == 1) and (1 <= file_name_len <= 1024):
            header_correct = True
        elif file_name_len != len(file_name):
            file_corrupted = True
        if not header_correct:
            raise Exception("Error: Header received from file did not match specified header format")
        if file_corrupted:
            raise Exception("Error: Length of file name did not match header specified file name length")
    except Exception as e:
        print(e)
    return header_correct, file_corrupted


def check_file_exists(file_name):
    """Checks if the file requested by the client can be opened for reading."""
    file_exists = True
    try:
        decoded_file = file_name.decode()
        f = open(decoded_file)
        f.close()
    except OSError:
        print("Error: file does not exist or cannot be opened")
        file_exists = False
    finally:
        return file_exists


def read_file_data(file_name):
    """Reads the data from the file specified by the client."""
    decoded_file = file_name.decode()
    file = open(decoded_file, 'rb')
    file_content = file.read()
    file_length = len(file_content)
    file.close()
    return file_content, file_length


def decide_file_response(header_correct, file_corrupted, file_exists, magic_no, file_name, client_socket):
    """Decides on which file response to send to the client depending on if the requested file exists or not.
    If the file could not be opened for reading, file_response_sent = 0, if it could, file_response_sent = 1."""
    file_response_sent = 0
    if header_correct and not file_corrupted and file_exists:
        send_type = 2
        status_code = 1
        file_data, file_length = read_file_data(file_name)
        file_response = create_file_response(magic_no, send_type, status_code, file_length, file_data)
        client_socket.send(file_response)
        file_response_sent = 1
    if not file_exists:
        file_data = 0
        empty_data = file_data.to_bytes(11, 'big')
        file_response = create_file_response(0x497E, 2, 0, 0, empty_data)
        client_socket.send(file_response)
    return file_response_sent, file_response


def create_file_response(magic_no, send_type, status_code, file_length, file_data):
    """Creates a file response byte array, given parameters in decimal format."""
    file_response = bytearray(0)
    file_response += magic_no.to_bytes(2, 'big')
    file_response += send_type.to_bytes(1, 'big')
    file_response += status_code.to_bytes(1, 'big')
    file_response += file_length.to_bytes(4, 'big')
    file_response += file_data
    return file_response


def main_server_loop(server_socket, port_num_s):
    """Infinite server loop which receives, processes and sends data to and from client."""
    while True:
        try:
            client_socket, client_address = server_socket.accept()
            print("Server is now connected to {} on port {} at {}".format(client_address[0], client_address[1],
                                                                          datetime.datetime.now()))
            bytes_recv = recv_bytes(server_socket, client_socket)
            if bytes_recv != 0:
                client_info = process_recv_bytes(bytes_recv)
                magic_no, send_type, file_name_len, file_name = client_info
                header_correct, file_corrupted = check_header(magic_no, send_type, file_name_len, file_name)
                file_exists = check_file_exists(file_name)
                file_response_sent, file_response = decide_file_response(header_correct, file_corrupted, file_exists,
                                                                         magic_no, file_name, client_socket)
                if file_response_sent == 1:
                    sent_bytes = len(file_response)
                    print("Sent {} bytes".format(sent_bytes))
        except KeyboardInterrupt:
            server_socket.close()
            sys.exit()
        except Exception as e:
            print(e)
            server_socket.close()
            break


def main_server():
    """Main server socket function."""
    port_num_s = check_cmd_args()
    if port_num_s is None:
        sys.exit()
    server_socket = server_set_up(port_num_s)
    if server_socket is None:
        print("Error: Unable to create server socket")
        sys.exit()
    else:
        main_server_loop(server_socket, port_num_s)


main_server()
