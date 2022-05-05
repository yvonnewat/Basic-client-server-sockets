# ------------------------------CLIENT SOCKET---------------------------------

import sys
import socket
import os.path


def client_set_up():
    """Creates the client socket."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1)
    except Exception as e:
        print(e)
    return client_socket


def read_cmd_args():
    """Gets client function arguments from the command line and checks they are valid."""
    args_invalid = 0
    try:
        prog_name, ip_name, port_num_c, file_name = sys.argv
        if os.path.isfile(file_name):
            raise FileExistsError("Unable to write to a file that already exists")
        if len(sys.argv) != 4:
            raise ValueError("Please enter an IP address or host name, port number between 1024 and 64000"
                             "\nand a file name")
        if int(port_num_c) < 1024 or int(port_num_c) > 64000:
            raise ValueError("Error: Please choose a port number between 1024 and 64000")
        if len(file_name) < 1:
            raise Exception("File name is too small")
        elif len(file_name) > 1024:
            raise Exception("File name is too long")
        else:
            list_info = socket.getaddrinfo(ip_name, port_num_c)
            tuple_info = list_info[0]
            connection_info = tuple_info[4]
            ip_address = connection_info[0]
    except Exception as e:
        print(e)
        args_invalid = 1
        return args_invalid
    else:
        return ip_address, int(port_num_c), file_name


def check_client_server_connection(client_socket, ip_address, port_num_c):
    """Checks that a connection can be established between the client and the server, without a gap of greater
    than one second, returns 1 if the connection is successful and 0 if it's unsuccessful."""
    try:
        client_socket.connect((ip_address, port_num_c))
        return 1
    except Exception as e:
        print(e)
        return 0


def send_and_recv(file_name, client_socket):
    """Sends file request to server and receives first data payload."""
    try:
        file_request = create_file_request(file_name)
        client_socket.send(file_request)
        bytes_recv = client_socket.recv(4096)
        header = bytes_recv[:8]
        is_corrupted, status_code, data_length = check_header(header)
        total_bytes_recv = bytes_recv[8:]
    except Exception as e:
        print(e)
    else:
        return is_corrupted, status_code, data_length, total_bytes_recv, header


def write_data_to_file(file_name, total_bytes_recv, data_length, client_socket, is_corrupted, status_code):
    """Given the server has located the file and sent the data, this function creates and opens the file for writing and
    writes the sent data into it."""
    file_opens = check_file_opens(file_name)
    if file_opens:
        file = open(file_name, 'wb')
        # write the first payload to the file
        file.write(total_bytes_recv)
    while not is_corrupted and status_code != 0 and data_length > len(total_bytes_recv):
        # receive file response from server -- in increments of 4096 bytes
        recv_bytes = client_socket.recv(4096)
        if len(recv_bytes) == 0:
            break
        else:
            total_bytes_recv += recv_bytes
            file.write(recv_bytes)
    file.close()
    return total_bytes_recv


def create_file_request(file_name):
    """Creates the file request to send to the server."""
    file_request = bytearray(0)
    magic_number = 0x497E
    type_file = 1
    filename_encoded = file_name.encode('utf-8')
    file_name_len = len(filename_encoded)
    file_request += magic_number.to_bytes(2, 'big')
    file_request += type_file.to_bytes(1, 'big')
    file_request += file_name_len.to_bytes(2, 'big')
    file_request += filename_encoded
    return file_request


def check_header(fixed_header):
    """Checks the validity of the file response from the server."""
    is_corrupted = False
    magic_num = int.from_bytes(fixed_header[:2], 'big')
    type_msg = int.from_bytes(fixed_header[2:3], 'big')
    status_code = int.from_bytes(fixed_header[3:4], 'big')
    data_length = int.from_bytes(fixed_header[4:], 'big')
    if magic_num != 0x497E or type_msg != 2:
        is_corrupted = True
    return is_corrupted, status_code, data_length


def check_file_opens(file_name):
    """Checks that the client is able to open the file for writing."""
    file_opens = True
    try:
        f = open(file_name, 'wb')
        f.close()
    except OSError:
        print("Error: could not open the file for writing")
        file_opens = False
    finally:
        return file_opens


def main_client():
    """Main client socket function."""
    try:
        client_socket = None
        args = read_cmd_args()
        if args == 1:
            raise Exception("Error: Arguments passed to client were invalid")
        else:
            ip_address, port_num_c, file_name = args
        client_socket = client_set_up()
        if client_socket is None:
            raise Exception("Error: Unable to set up client socket")
        check_num = check_client_server_connection(client_socket, ip_address, port_num_c)
        if check_num == 0:
            raise Exception("Error: Unable to connect to server")
        data = send_and_recv(file_name, client_socket)
        if data is None:
            raise Exception("Error: Client experienced issues while sending and receiving data")
        else:
            is_corrupted, status_code, data_length, total_bytes_recv, header = data
            if is_corrupted:
                raise Exception("Error: File response record was invalid")
            if status_code == 0:
                raise Exception("Error: Server could not send the indicated file")
            else:
                total_recv = write_data_to_file(file_name, total_bytes_recv, data_length, client_socket, is_corrupted,
                                                status_code)
                total_bytes_as_int = len(header + total_recv)
                expected_bytes_int = len(header) + data_length
                if total_bytes_as_int != expected_bytes_int:
                    raise Exception("Error: Length of data sent did not match the data length as indicated in the file "
                                    "response record")
                print("Received {0} bytes, expected {1} bytes".format(total_bytes_as_int, expected_bytes_int))
    except Exception as e:
        print(e)
        if client_socket is not None:
            client_socket.close()
        sys.exit()
    else:
        client_socket.close()
        sys.exit()


main_client()


