'''
This Python script is a TUI WiFi manager, allowing beepy users to control WiFi connections via the terminal. It displays connected and #available networks, enables connection, turning WiFi on/off, scanning networks, and forgetting connections. Users navigate with arrow keys, #connect with Enter, and quit with 'q' , and help with 'h'.

Author: abdallah natsheh @darkswordman
Date: 19-4-2024

'''
import curses
import time
import subprocess
import argparse  # Import argparse for command line argument parsing

# Global variables to store network information
connected_network = None
available_networks = []

def get_wifi_ip_address():
    try:
        # Run nmcli command to get device information
        result = subprocess.run(['nmcli', '-p', 'device', 'show'], capture_output=True, text=True, check=True)
        
        # Split the output by lines
        lines = result.stdout.split('\n')
        
        # Initialize variables to store device and IP information
        device_name = None
        ip_address = None
        
        # Loop through each line to find WiFi device and IP address
        for line in lines:
            if 'GENERAL.DEVICE:' in line:
                device_name = line.split(':')[1].strip()
            elif device_name and device_name.startswith('wlan') and 'IP4.ADDRESS' in line:
                ip_address = line.split(':')[1].split('/')[0].strip()
                # If IP address is found, break the loop
                break
        
        return ip_address
    
    except subprocess.CalledProcessError:
        # If nmcli command fails, return None
        return None

def get_connected_network():
    global connected_network
    try:
        # Run nmcli to get information about the active connection
        result = subprocess.run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"], capture_output=True, text=True)
        if result.returncode == 0:
            connected_network = result.stdout.strip()
        else:
            connected_network = None
    except Exception as e:
        print(f"Error: {e}")
        connected_network = None

def get_wifi_status():
    try:
        # Run nmcli to get the status of WiFi
        result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
        status = result.stdout.strip()
        return status == "enabled"
    except Exception as e:
        print(f"Error: {e}")
        return False

def turn_wifi_on():
    try:
        # Run nmcli to turn on WiFi
        subprocess.run(["nmcli", "radio", "wifi", "on"])
    except Exception as e:
        print(f"Error: {e}")

def turn_wifi_off():
    try:
        # Run nmcli to turn off WiFi
        subprocess.run(["nmcli", "radio", "wifi", "off"])
    except Exception as e:
        print(f"Error: {e}")

def get_available_networks():
    global available_networks
    try:
        # Run nmcli to get the list of available networks
        result = subprocess.run(["nmcli", "-f", "SSID,SECURITY,SIGNAL", "device", "wifi", "list"], capture_output=True, text=True)
        output_lines = result.stdout.splitlines()[1:]  # Skip the header line
        networks = []
        for line in output_lines:
            line_values = line.split()
            ssid = line_values[0]
            if ssid and ssid != '--':  # Check if SSID is not empty (not a hidden network)
                security = ' '.join(line_values[1:-1])  # Join all elements from index 1 to second-to-last
                signal = line_values[-1]
                networks.append({"name": ssid, "protected": "none" not in security, "strength": int(signal)})
        available_networks = networks
    except Exception as e:
        print(f"Error: {e}")
        available_networks = []

def scan_networks():
    try:
        # Run nmcli to rescan available networks
        subprocess.run(["nmcli", "device", "wifi", "rescan"])
    except Exception as e:
        print(f"Error: {e}")

def forget_network(network_name):
    try:
        # Run nmcli to forget the specified network
        subprocess.run(["nmcli", "connection", "delete", network_name])
    except Exception as e:
        print(f"Error forgetting network {network_name}: {e}")

def show_header(stdscr, wifi_enabled):
    global connected_network
    if wifi_enabled:
        if connected_network:
            stdscr.addstr(f"Connected to: {connected_network} - {get_wifi_ip_address()}\n")
        stdscr.addstr(f"Available {len(available_networks)} Networks:\n")
    else:
        stdscr.addstr(f"WiFi: Off")

def draw_network_list(stdscr, start_index, selected_index, wifi_enabled):
    global available_networks
    if wifi_enabled:
        global connected_network
        height, width = stdscr.getmaxyx()
        for i, network in enumerate(available_networks[start_index:start_index + min(4, height - 5)]):
            box = curses.newwin(3, curses.COLS - 2, i * 3 + 2, 1)
            box.border()
            if i + start_index == selected_index:
                box.attron(curses.color_pair(1))
            signal_strength_bar = ''.join(['|' for _ in range(int(network['strength']/20))])
            box.addstr(1, 2, f"{network['name']} {signal_strength_bar}")
            if network['protected']:
                box.addstr(1, curses.COLS - 9, '[P]')
            if network['name'] == connected_network:
                box.addstr(1, curses.COLS - 6, '[*]')
            box.refresh()
            if i + start_index == selected_index:
                box.attroff(curses.color_pair(1))
    else:
        box = curses.newwin(3, curses.COLS - 2, 5, 1)
        box.border()
        box.addstr(1, 2, f"WIFI OFF PRESS o/O TO TURN IT ON")
        box.refresh()

    stdscr.refresh()

def show_loading_animation(stdscr):
    stdscr.addstr("\nConnecting...")
    for _ in range(3):
        for c in '|/-\\':
            stdscr.addstr(c)
            stdscr.refresh()
            time.sleep(0.1)

def show_connecting_dialog(stdscr, network):
    stdscr.clear()
    stdscr.addstr(f"Connecting to {network['name']}...\n")
    stdscr.addstr(f"Press Esc to return or any key to connect.\n")
    key = stdscr.getch()
    if key == 27:  # Enter or Esc key
        return
    else:
        if network['protected']:
            saved_connections = subprocess.run(["nmcli", "connection", "show"], capture_output=True, text=True)
            if saved_connections.returncode == 0 and network['name'] in saved_connections.stdout:
                # Network is already connected with saved password
                stdscr.clear()
                stdscr.addstr("Attempting to connect without password...\n")
                show_loading_animation(stdscr)
                try:
                    # Try to connect to the network using nmcli
                    subprocess.run(["nmcli", "connection", "up", network['name']], check=True)
                    get_connected_network()
                    stdscr.addstr("\nConnected!\nPress Enter to continue...")
                except subprocess.CalledProcessError:
                    stdscr.addstr("\nFailed to connect!\nPress Enter to continue...")
            else:
                # Network requires password entry
                stdscr.addstr("Enter Password: ")
                curses.echo()
                stdscr.refresh()
                password = stdscr.getstr().decode("utf-8")
                curses.noecho()
                stdscr.clear()
                show_loading_animation(stdscr)
                try:
                    # Try to connect to the network using nmcli
                    subprocess.run(["nmcli", "device", "wifi", "connect", network['name'], "password", password], check=True)
                    get_connected_network()
                    stdscr.addstr("\nConnected!\nPress Enter to continue...")
                except subprocess.CalledProcessError:
                    stdscr.addstr("\nFailed to connect!\nPress Enter to continue...")
        else:
            show_loading_animation(stdscr)
            try:
                # Try to connect to the network using nmcli
                subprocess.run(["nmcli", "device", "wifi", "connect", network['name']], check=True)
                get_connected_network()
                stdscr.addstr("\nConnected!\nPress Enter to continue...")
            except subprocess.CalledProcessError:
                stdscr.addstr("\nFailed to connect!\nPress Enter to continue...")

def main(stdscr):
    curses.curs_set(0)  # Hide the cursor
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Highlighted box color pair
    wifi_enabled = get_wifi_status()
    get_connected_network()  # Retrieve initial connected network
    get_available_networks()  # Retrieve initial available networks
    selected_index = 0
    start_index = 0
    first_run = True
    key = None
    stdscr.clear()
    show_header(stdscr, wifi_enabled)
    while True:
        draw_network_list(stdscr, start_index, selected_index, wifi_enabled)
        if first_run is not True:
            key = stdscr.getch()
        first_run = False
        if key == curses.KEY_UP and selected_index > 0:
            selected_index -= 1
            if selected_index < start_index:
                start_index = max(0, selected_index)
            stdscr.clear()
            show_header(stdscr, wifi_enabled)
        elif key == curses.KEY_DOWN and selected_index < len(available_networks) - 1:
            selected_index += 1
            if selected_index >= start_index + min(4, curses.LINES - 5):
                start_index += 1
            stdscr.clear()
            show_header(stdscr, wifi_enabled)
        elif key == ord('\n'):
            if wifi_enabled:
                network = available_networks[selected_index]
                show_connecting_dialog(stdscr, network)
                key = stdscr.getch()
                if key == ord('\n') or key == 27:  # Enter or Esc key
                    stdscr.clear()
                    selected_index = 0  # Reset selected index
                    start_index = 0
                    show_header(stdscr, wifi_enabled)
        elif key == ord('o'):
            if wifi_enabled:
                # Show a confirmation dialog to turn off WiFi
                stdscr.clear()
                stdscr.addstr("Are you sure you want to turn off WiFi? (Y/N)\n")
                confirmation_key = stdscr.getch()
                if confirmation_key == ord('Y') or confirmation_key == ord('y'):
                    turn_wifi_off()
                    wifi_enabled = False
                    selected_index = 0
                    start_index = 0
                    stdscr.clear()
                    show_header(stdscr, wifi_enabled)
                elif confirmation_key == ord('N') or confirmation_key == ord('n'):
                    stdscr.clear()
                    show_header(stdscr, wifi_enabled)
            else:
                turn_wifi_on()
                wifi_enabled = True
                stdscr.clear()
                show_header(stdscr, wifi_enabled)
        elif key in (ord('s'), ord('S')):
            scan_networks()
            get_available_networks()  # Update available networks after scanning
            stdscr.clear()
            show_header(stdscr, wifi_enabled)
        elif key == ord('f') or key == ord('F'):
            if wifi_enabled:
                network_to_forget = available_networks[selected_index]
                if network_to_forget['name'] == connected_network:
                    stdscr.clear()
                    stdscr.addstr("Cannot forget the currently connected network.\nPress Enter to continue...")
                else:
                    forget_network(network_to_forget['name'])
                    stdscr.clear()
                    stdscr.addstr(f"Forgot network: {network_to_forget['name']}\nPress Enter to continue...")
                    get_connected_network()  # Refresh connected network after forgetting
                key = stdscr.getch()
                if key == ord('\n'):
                    stdscr.clear()
                    selected_index = 0  # Reset selected index
                    start_index = 0
                    show_header(stdscr, wifi_enabled)
        elif key == ord('q') or key == ord('Q'):
            break
        elif key == ord('h'):
            stdscr.clear()
            stdscr.addstr("Commands:\n")
            stdscr.addstr("- Up/Down Arrow: Navigate network list\n")
            stdscr.addstr("- Enter: Connect to selected network\n")
            stdscr.addstr("- s: Scan for available networks\n")
            stdscr.addstr("- f: Forget selected network\n")
            stdscr.addstr("- o: Turn WiFi on/off\n")
            stdscr.addstr("- q: Quit\n")
            stdscr.addstr("Press any key to return to the network list...")
            stdscr.refresh()
            key = stdscr.getch()
            stdscr.clear()
            show_header(stdscr, wifi_enabled)
        stdscr.refresh()

if __name__ == "__main__":
    curses.wrapper(main)
