import sys
import os
import shutil
import sqlite3
import re
import hashlib
import logging
from math import floor
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QInputDialog,
    QMessageBox,
    QTableWidgetItem,
    QFileDialog,
    QStackedWidget,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QTableWidget,
    QHeaderView,
    QStyleFactory,
    QLineEdit
)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QSize
from PIL import Image
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore
from datetime import datetime

# Set up logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
logs_file = 'logs.txt'
file_handler = logging.FileHandler(logs_file)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)
logging.getLogger().handlers.clear()

# Set up event logger
eventlogger = logging.getLogger('eventslogger')
eventlogger.setLevel(logging.INFO)
eventfile = 'logs.txt'
eventhandler = logging.FileHandler(eventfile)
eventhandler.setLevel(logging.INFO)
eventformatter = logging.Formatter('%(asctime)s - %(message)s')
eventhandler.setFormatter(eventformatter)
eventlogger.addHandler(eventhandler)

# Set up order logger
orderlogger = logging.getLogger('orderslogger')
orderlogger.setLevel(logging.INFO)
timenow = datetime.now()
orderfile = f'{timenow} items.txt'
orderhandler = logging.FileHandler(orderfile)
orderhandler.setLevel(logging.INFO)
orderformatter = logging.Formatter('%(asctime)s - %(message)s')
orderhandler.setFormatter(orderformatter)
orderlogger.addHandler(orderhandler)

# Set up last logger
lastlogger = logging.getLogger('lastlogger')
lastlogger.setLevel(logging.INFO)
lastfile = f'{timenow} sales.txt'
lasthandler = logging.FileHandler(lastfile)
lasthandler.setLevel(logging.INFO)
lastformatter = logging.Formatter('%(message)s')
lasthandler.setFormatter(lastformatter)
lastlogger.addHandler(lasthandler)

def log_event(event):  # Log events
    eventlogger.info(event)

pizzasales = {}

def log_order(orders, user):  # Log orders
    for order in orders:
        formattedorder = ','.join(map(str, order))  # Convert order list to a string
        formattedorder += f' - {user}'  # Append username to the order
        orderlogger.info(formattedorder)  # Log the formatted order

        # Extract pizza information from the order
        type = order[1]
        quantity = int(order[3])
        price = (float(order[2])/100)

        # Update pizza sales data
        if type in pizzasales:
            pizzasales[type]['quantity'] += quantity
            pizzasales[type]['amount'] += quantity * price
        else:
            pizzasales[type] = {'quantity': quantity, 'amount': quantity * price}

def process_orders():  # Generate sales table
    table = f"{'Pizza Type':<20} {'Quantity':<10} {'Total Amount':<20}\n"
    for type, data in pizzasales.items():
        table += f"{type:<20} {data['quantity']:<10} ${data['amount']:<20.2f}\n"
    
    lastlogger.info(table)

def copy_file(source_path, destination_directory, new_name):  # Copy a file
    file_name, extension = os.path.splitext(source_path)
    destination_path = os.path.join(destination_directory, new_name + extension)
    try:
        shutil.copy(source_path, destination_path)
    except FileNotFoundError:
        return False
    return destination_path

def resize_to_square(image_path, size):  # Resize image to a square
    image = Image.open(image_path)
    image.thumbnail((size, size))
    new_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    new_image.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    os.remove(image_path)
    return new_image

def convert_to_png(image_path):  # Convert an image to PNG format
    image = Image.open(image_path)
    converted_image = image.convert("RGBA")
    return converted_image

def convert_and_delete_original(image_path):  # Convert an image to PNG and delete the original
    directory, filename = os.path.split(image_path)
    filename_without_extension, extension = os.path.splitext(filename)
    png_filename = f"{filename_without_extension}.png"
    converted_image = convert_to_png(image_path)
    converted_image_path = os.path.join(directory, png_filename)
    converted_image.save(converted_image_path, "PNG")
    os.remove(image_path)
    return converted_image_path

def convert_to_money_and_add(money, row, column, table, neg=None):  # Convert float to money format and add to table
    value = str(money)
    if neg:
        value = f"-${value[:-2]}.{value[-2:]}"
    else:
        value = f"${value[:-2]}.{value[-2:]}"
    item = QTableWidgetItem(str(value))
    table.setItem(row, column, item)

class NaturalScrollTable(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def wheelEvent(self, event):  # Handle wheel scrolling
        # Get scrolling delta
        delta = event.angleDelta().y()

        if delta > 0:
            self.verticalScrollBar().setSliderPosition(
                self.verticalScrollBar().sliderPosition() - self.verticalScrollBar().singleStep()
            )
        else:
            self.verticalScrollBar().setSliderPosition(
                self.verticalScrollBar().sliderPosition() + self.verticalScrollBar().singleStep()
            )
        # Inverts the scrolling
        event.accept()

class HomeScreen(QDialog): # Screen to see on execution
    def __init__(self):
        super(HomeScreen, self).__init__()
        loadUi("welcome.ui", self)
        self.login.clicked.connect(self.gotologin)
        self.newacc.clicked.connect(self.gotonewacc)

    def gotologin(self): #button links to log in
        login = LoginScreen()
        widget.addWidget(login)
        widget.setCurrentIndex(widget.currentIndex()+1)

    def gotonewacc(self): #button links to new account
        newacc = NewaccScreen()
        widget.addWidget(newacc)
        widget.setCurrentIndex(widget.currentIndex()+1)
        
    def keyPressEvent(self, event): #prevent screen from being flashed
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)

class LoginScreen(QDialog): # Login screen
    user = ""  # Initialize a class variable to store the logged-in user
    
    def __init__(self):
        super(LoginScreen, self).__init__()
        loadUi("login.ui", self)  # Load the UI file for the login dialog
        self.returnbutton.setStyleSheet("""QPushButton {
                border-image: url(./images/assets/return.png) 0 0 0 0 stretch stretch;}""")
        self.returnbutton.clicked.connect(self.returnhome)  # Connect return button click event to returnhome method
        self.passwordfield.setEchoMode(QLineEdit.Password)  # Set password field to show dots for input
        self.loginbutton.clicked.connect(self.loginfunction)  # Connect login button click event to loginfunction method
        self.usernamefield.returnPressed.connect(self.loginfunction)  # Connect enter key press in username field to loginfunction
        self.passwordfield.returnPressed.connect(self.loginfunction)  # Connect enter key press in password field to loginfunction
        # Set up fields and buttons in the UI

    def returnhome(self):  # Method to return to the welcome screen
        widget.addWidget(home)
        widget.setCurrentIndex(widget.currentIndex() + 1)
    
    def loginfunction(self):  # Method to attempt login
        LoginScreen.user = self.usernamefield.text()  # Get the username entered
        self.user = LoginScreen.user
        password = self.passwordfield.text()  # Get the password entered

        if len(self.user) == 0 or len(password) == 0:  # Check if username or password fields are empty
            self.error.setText("Please input all fields.")
        elif not re.match("^[a-zA-Z0-9]+$", self.user):  # Check if username contains only letters and numbers
            self.error.setText("Inputs only allow letters and numbers.")
        elif not re.match("^[a-zA-Z0-9]+$", password):  # Check if password contains only letters and numbers
            self.error.setText("Inputs only allow letters and numbers.")
        else:
            conn = sqlite3.connect("cs.db")
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM logins WHERE username = ?", (self.user,))
            result_usercount = cur.fetchone()[0]
            
            if result_usercount > 0:  # Check if user exists in the database
                cur.execute("SELECT password FROM logins WHERE username = ?", (self.user,))
                result_pass = cur.fetchone()[0]
                hashobj = hashlib.sha512()
                hashobj.update(password.encode())
                hashedpass = hashobj.hexdigest()

                if result_pass == hashedpass:  # Check if the hashed password matches the one in the database
                    print("Successfully logged in")
                    self.error.setText("")
                    cur.execute("SELECT admin FROM logins WHERE username = ?", (self.user,))
                    admin = cur.fetchone()[0]
                    
                    if admin:  # Check if the user is an admin
                        log_event("Admin logged in.")
                        program = AdminProgram()
                    else:
                        log_event(f"User '{self.user}' logged in.")
                        program = Program()
                    widget.addWidget(program)
                    widget.setCurrentIndex(widget.currentIndex() + 1)
                else:
                    self.error.setText("Invalid username or password")
            else:
                self.error.setText("Invalid username or password")
                
    def keyPressEvent(self, event):  # Method to handle key press events
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)
            
class NewaccScreen(QDialog): # Create account screen
    def __init__(self):
        super(NewaccScreen, self).__init__()
        loadUi("newacc.ui", self)
        self.returnbutton.setStyleSheet("""QPushButton {
                border-image: url(./images/assets/return.png) 0 0 0 0 stretch stretch;}""")
        self.returnbutton.clicked.connect(self.returnhome)
        self.passwordfield.setEchoMode(QLineEdit.Password)
        self.confirmfield.setEchoMode(QLineEdit.Password)
        self.createbutton.clicked.connect(self.createfunction)
        self.usernamefield.returnPressed.connect(self.createfunction)
        self.passwordfield.returnPressed.connect(self.createfunction)
        self.confirmfield.returnPressed.connect(self.createfunction)
        # Set fields
        
    def createfunction(self):
        # Get user input from text fields
        user = self.usernamefield.text()
        password = self.passwordfield.text()
        confirm = self.confirmfield.text()
        
        # Check if any field is empty
        if len(user) == 0 or len(password) == 0 or len(confirm) == 0:
            self.error.setText("Please input all the fields.")
        # Check if input contains only letters and numbers
        elif not re.match("^[a-zA-Z0-9]+$", user):
            self.error.setText("Inputs only allow letters and numbers.")
        elif not re.match("^[a-zA-Z0-9]+$", password):
            self.error.setText("Inputs only allow letters and numbers.")
        elif not re.match("^[a-zA-Z0-9]+$", confirm):
            self.error.setText("Inputs only allow letters and numbers.")
        else:
            # Database connection
            conn = sqlite3.connect("cs.db")
            cur = conn.cursor()
            
            # Check if username already exists
            cur.execute(f"SELECT COUNT(*) FROM logins WHERE username = ?", (user,))
            result_usercount = cur.fetchone()[0]
            if result_usercount > 0:
                self.error.setText("This username has been taken.")
            # Check if password and confirmation match
            elif password != confirm:
                self.error.setText("The confirmation does not match.")
            else:
                # Hash the password for security
                hashobj = hashlib.sha512()
                hashobj.update(password.encode())
                hashedpass = hashobj.hexdigest()
                
                # Set loyalty flag if checkbox is checked
                loyalty = 0
                if self.loyalty.isChecked():
                    loyalty = 1
                
                # Insert user data into the database
                cur.execute('INSERT INTO logins (username, password, admin ,loyalty) VALUES (?, ?, 0, ?)', (user, hashedpass, loyalty))
                conn.commit()
                conn.close()
                
                # Log user creation event
                log_event(f"{loyalty*'Loyalty '}User '{user}' was created.")
                
                # Clear error message and navigate to home screen
                self.error.setText("")
                widget.addWidget(home)
                widget.setCurrentIndex(widget.currentIndex()+1)


    def returnhome(self):
        widget.addWidget(home)
        widget.setCurrentIndex(widget.currentIndex()+1)
    
    def keyPressEvent(self, event):
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)

class AdminProgram(QDialog): # Admin program
    def __init__(self):
        super(AdminProgram, self).__init__()
        # Load the UI file
        loadUi("admin.ui", self)
        # Set window title
        main.setWindowTitle("Admin Panel")
        # Set up the table
        self.alltable.setColumnCount(5)
        self.alltable.setRowCount(0)
        self.alltable.setHorizontalHeaderLabels(["Pizza ID", "Pizza", "Cost", "", ""])
        self.alltable.verticalHeader().setVisible(False)
        self.alltable.setEditTriggers(QTableWidget.NoEditTriggers)
        # Connect logout button to function
        self.logoutbutton.clicked.connect(self.logout)
        # Initialize table
        self.settable()

    def logout(self):
        # Log admin logout event
        log_event("Admin logged out.")
        # Clear current user
        LoginScreen().user = ""
        # Navigate back to home screen
        widget.addWidget(home)
        widget.setCurrentIndex(widget.currentIndex()+1)
        
    def settable(self):
        # Set up table with items from the database
        conn = sqlite3.connect("cs.db")
        cur = conn.cursor()
        cur.execute('SELECT * FROM item')
        self.itemlist = cur.fetchall()
        self.alltable.clearContents()
        self.alltable.setRowCount(0)
        # Populate the table
        for row_number, row_data in enumerate(self.itemlist):
            self.alltable.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                self.alltable.setItem(row_number, column_number, QTableWidgetItem(str(data)))
            # Add edit and remove buttons to each row
            button = QPushButton("edit")
            button.clicked.connect(lambda _, row=row_number: self.edit(row))
            self.alltable.setCellWidget(row_number, 3, button)
            button = QPushButton("remove")
            button.clicked.connect(lambda _, row=row_number: self.remove(row))
            self.alltable.setCellWidget(row_number, 4, button)
        # Add button for adding new item
        self.alltable.insertRow(len(self.itemlist))
        button = QPushButton("add")
        button.clicked.connect(self.add)
        self.alltable.setCellWidget(len(self.itemlist), 0, button)

    def add(self):
        # Add a new item to the database
        setname = ""
        while setname == "" or any(setname.lower() in items[1].lower() for items in self.itemlist): 
            setname, ok = QInputDialog.getText(self, "Name", "Enter a name for the pizza")
            if ok:
                if setname.isspace():
                    setname = ""
                    QMessageBox.warning(self, "Error", "Do not use space as a name")
                elif len(setname) > 18:
                    setname = ""
                    QMessageBox.warning(self, "Error", "18 characters max")    
            else:
                return False
        setprice, ok = QInputDialog.getInt(self, "Price,", "Enter a price for the pizza (cents)", 1, 1, 10000)
        if not ok:
            return False
        # Add image for the new item
        filedialog = QFileDialog()
        imagepath, _ = filedialog.getOpenFileName(None, "Select File")
        if imagepath:
            path = copy_file(imagepath, "./images", (setname))
            if path:
                convert_and_delete_original(path)
                response = QMessageBox.question(None, "Delete", "Do you wish to delete original file?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if response == QMessageBox.Yes:
                    os.remove(imagepath)
        # Insert new item into the database
        conn = sqlite3.connect("cs.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO item VALUES (NULL, ?, ?)", (setname, setprice))
        conn.commit()
        cur.close()
        conn.close()
        # Log the addition of the new item
        log_event(f"Pizza '{setname}' has been added.")
        # Refresh the table
        self.settable()

    def remove(self, row):
        # Remove item from the database
        id = self.itemlist[row][0]
        name = self.itemlist[row][1]
        conn = sqlite3.connect("cs.db")
        cur = conn.cursor()
        response = QMessageBox.question(None, "Confirm", "Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.Yes:
            cur.execute('DELETE FROM item WHERE itemID = ?', (id,))
        try:
            os.remove(f"./images/{name}-square.png")
        except(FileNotFoundError):
            pass
        conn.commit()
        cur.close()
        conn.close()
        # Log the removal of the item
        log_event(f"Pizza '{name}' has been removed.")
        # Refresh the table
        self.settable()

    def edit(self, row):
        # Edit item in the database
        id = self.itemlist[row][0]
        defaultname = self.itemlist[row][1]
        defaultprice = self.itemlist[row][2]
        setname = ""
        while setname == "":
            setname, ok = QInputDialog.getText(self, "Name", "Enter a name for the pizza", text=defaultname)
            if ok:
                if setname.isspace():
                    setname = ""
                    QMessageBox.warning(self, "Error", "Do not use space as a name")
                for items in self.itemlist:
                    if setname.lower() == items[1].lower() and defaultname != items[1]:
                        setname = ""
            else:
                return False
        setprice, ok = QInputDialog.getInt(self, "Price,", "Enter a price for the pizza (cents)", defaultprice, 1, 10000)
        if not ok:
            return False
        response = QMessageBox.question(None, "Image", "Choose new image?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.Yes:
            filedialog = QFileDialog()
            imagepath, _ = filedialog.getOpenFileName(None, "Select File")
            if imagepath:
                path = copy_file(imagepath, "./images", (setname))
                if path:
                    convert_and_delete_original(path)
                    response = QMessageBox.question(None, "Delete", "Do you wish to delete original file?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if response == QMessageBox.Yes:
                        os.remove(imagepath)
            else:
                return False
        elif setname != defaultname:
            try:
                os.rename(f"./images/{defaultname}-square.png", f"./images/{setname}-square.png")
            except(FileNotFoundError):
                pass
        # Update the item in the database
        conn = sqlite3.connect("cs.db")
        cur = conn.cursor()
        cur.execute("UPDATE item SET name = ?, price = ? WHERE itemID = ?", (setname, setprice, id))
        conn.commit()
        cur.close()
        conn.close()
        # Log the editing of the item
        log_event(f"Pizza '{setname}' has been edited.")
        # Refresh the table
        self.settable()
    
    def modifyUsers(self): #modifying the users
        # This method is not implemented yet
        raise NotImplementedError
    
    def modifyOrders(self): #modifying the orders
        # This method is not implemented yet
        raise NotImplementedError

    def keyPressEvent(self, event):
        # Override key press event to handle Escape key
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)

class Program(QDialog): # Main program for users
    loyalty = 0  # Default loyalty points for the program

    def __init__(self):
        super(Program, self).__init__()
        loadUi("main.ui", self)  # Load the UI file
        conn = sqlite3.connect("cs.db")  # Connect to the SQLite database
        cur = conn.cursor()  # Create a cursor object
        query = 'SELECT * FROM item'  # SQL query to select all items
        cur.execute(query)  # Execute the query
        allitems = cur.fetchall()  # Fetch all items from the database
        logins = LoginScreen()  # Create an instance of the LoginScreen class
        cur.execute('SELECT loyalty FROM logins WHERE username = ?', (logins.user,))  # Select loyalty points for the user
        self.loyalty = cur.fetchone()[0]  # Fetch loyalty points for the user
        self.resize(100, 100)  # Set the initial size of the window
        # Create layout for the main window
        self.layout = QtWidgets.QHBoxLayout(self)
        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.gridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.layout.addWidget(self.scrollArea)
        # Create a table to display the order details
        self.ordertable = NaturalScrollTable()
        self.ordertable.setColumnCount(6)
        self.ordertable.setRowCount(0)
        self.ordertable.setHorizontalHeaderLabels(["Pizza ID", "Pizza", "Cost", "Quantity", "Subtotal", "Total"])
        self.ordertable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ordertable.verticalHeader().setVisible(False)
        self.ordertable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ordertable.setColumnWidth(4, 130)
        self.gridLayout.addWidget(self.ordertable, 0, 0, 2, 3)
        self.gridLayout.setRowStretch(0, 4)
        self.gridLayout.setSpacing(4)

        # Create buttons for profile and order
        self.profilebutton = QPushButton("Profile", self)
        self.profilebutton.setFixedSize(QSize(230, 200))
        self.profilebutton.clicked.connect(self.goprofile)
        self.orderbutton = QPushButton("Order", self)
        self.orderbutton.setFixedSize(QSize(230, 100))
        self.orderbutton.clicked.connect(self.submit_order)
        self.gridLayout.addWidget(self.profilebutton, 0, 3)
        self.gridLayout.addWidget(self.orderbutton, 1, 3)

        # Initialize variables for order and item lists
        self.iddictionary = {}
        self.orderlist = []
        self.itemlist = []

        # Set background color of the window
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(255, 191, 0))
        self.setPalette(palette)

        # Create button for home delivery
        self.homedeliverybutton = QPushButton("Home Delivery")
        self.homedeliverybutton.setFixedSize(QSize(230, 230))
        self.homedeliverybutton.clicked.connect(self.delivery)
        self.delivery = 0  # Initialize delivery option to False
        self.gridLayout.addWidget(self.homedeliverybutton, 2, 0)

        # Iterate through all items to create buttons dynamically
        for number, data in enumerate(allitems):
            # Extract pizza name and cost
            buttontext = str(data[1])
            buttoncost = str(data[2])
            buttoncost = f"${buttoncost[:-2]}.{buttoncost[-2:]}"  # Format cost as currency
            button = QPushButton()  # Create a new button
            # Adjust button text size based on length
            if len(buttontext) > 7:
                textsize = 210 / len(buttontext)
            else:
                textsize = 30
            # Create labels for pizza name and cost
            textlabel = QLabel(buttontext)
            textlabel.setStyleSheet(f'font: bold {textsize}pt "Sans Serif Collection";')
            costlabel = QLabel(buttoncost)
            costlabel.setStyleSheet('font: bold 25pt "Sans Serif Collection";')
            layout = QVBoxLayout()
            layout.addWidget(textlabel)
            layout.addWidget(costlabel)
            layout.setAlignment(textlabel, Qt.AlignHCenter)
            layout.setAlignment(costlabel, Qt.AlignHCenter)
            button.setFixedSize(QSize(230, 230))
            button.setLayout(layout)
            # Set button style and connect click event
            try:
                newimage = resize_to_square(f"./images/{buttontext}.png", 230)
                newimage.save(f"./images/{buttontext}-square.png")
            except(FileNotFoundError):
                pass
            button.setStyleSheet("""QPushButton {padding: 0px 0 0px 0;
                font: bold 25pt "Sans Serif Collection";
                border: 2px solid rgb(80,0,140);
                color: rgb(80,0,140);
                background-image: url(./images/""" + buttontext + """-square.png);
                }""")
            button.clicked.connect(lambda _, row=floor(number / 4), col=number: self.button_clicked(row, col))
            self.gridLayout.addWidget(button, floor((number + 1) / 4) + 2, (number + 1) % 4)
            self.iddictionary[(floor(number / 4), number)] = data[0]  # Map button position to pizza ID
            appenddata = [data[0], data[1], data[2], 0, 0]
            self.itemlist.append(appenddata)  # Add item to item list

    def delivery(self):
        # Toggle delivery option
        if self.delivery:
            self.delivery = 0
        elif len(self.orderlist) > 0:
            self.delivery = 1
        else:
            QMessageBox.warning(self, "Status", "No items in your order.")
        self.update_table()
        pass

    def submit_order(self):
        # Submit the order
        if len(self.orderlist) > 0:
            log_order(self.orderlist, LoginScreen.user)  # Log the order
            conn = sqlite3.connect("cs.db")
            cur = conn.cursor()
            logins = LoginScreen()
            # Insert order details into the database
            cur.execute('INSERT INTO orders (username, orderlist, delivery) VALUES(?, ?, ?)',
                        (logins.user, str(self.orderlist), self.delivery))
            conn.commit()
            self.orderlist.clear()
            self.update_table(True)
            log_event(f"User '{logins.user}' made an order.")  # Log the event
            QMessageBox.information(self, "Status", "Order has been placed!")
        else:
            QMessageBox.warning(self, "Status", "No items in your order.")
            return False

    def goprofile(self):
        # Open the profile window
        profile = Profile()
        widget.addWidget(profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def button_clicked(self, row, col):
        # Handle button click event
        itemid = self.iddictionary[(row, col)]  # Get the pizza ID of the clicked button
        matching_list = next((t for t in self.itemlist if t[0] == itemid), None)  # Find the matching pizza in the list
        self.add_item(matching_list)  # Add the pizza to the order

    def add_item(self, data):
        # Add item to the order list
        inorders = False
        defval = 0  # Default quantity of pizza to display on UI
        for number, orders in enumerate(self.orderlist):
            if data[0] in orders:  # Check if the item is already in the order
                inorders = True
                defval = self.orderlist[number][3]  # Default quantity changes to existing quantity
        quantity, ok = QInputDialog.getInt(self, "Quantity", f"Enter the quantity for {data[1]} Pizza", defval, 0, 100)
        if ok:
            if inorders == False:  # If not in orders already
                cost = data[2] * quantity
                self.orderlist.append([data[0], data[1], data[2], quantity, cost])
                self.update_table()
            else:
                for item in self.orderlist:  # Change values in existing order
                    if item[0] == data[0]:
                        item[3] = quantity
                        cost = quantity * data[2]
                        item[4] = cost
                        self.update_table()
                        break
        return False

    def update_table(self, clear=None):
        # Update the order table
        if not clear:
            self.ordertable.clearContents()
            self.ordertable.setRowCount(0)
            self.orderlist.sort(key=lambda x: x[0])
            for items in self.orderlist:
                if items[3] == 0:
                    self.orderlist.remove(items)
                    if len(self.orderlist) > 0:
                        self.ordertable.setRowCount(len(self.orderlist) + 1)
                elif len(self.orderlist) + 1 >= self.ordertable.rowCount():
                    self.ordertable.setRowCount(len(self.orderlist) + 1)
            if not len(self.orderlist):
                self.delivery = 0
            for number, items in enumerate(self.orderlist):
                for i, column_index in enumerate([0, 1, 2, 3, 4]):
                    if i in [0, 1]:
                        value = items[i]
                    elif i == 2:
                        value = str(items[i])
                        value = f"${value[:-2]}.{value[-2:]}"
                    elif i == 3:
                        value = items[i]
                    else:
                        value = str(items[i])
                        value = f"${value[:-2]}.{value[-2:]}"
                    item = QTableWidgetItem(str(value))
                    self.ordertable.setItem(number, column_index, item)
                if number == len(self.orderlist) - 1:
                    summedcost = sum(item[4] for item in self.orderlist)
                    convert_to_money_and_add(summedcost, number, 5, self.ordertable)
                    deliverycost = 0
                    if self.delivery:
                        deliverycost = 800
                        self.ordertable.insertRow(number + 2)
                        self.ordertable.setItem(number + 1, 3, QTableWidgetItem("Delivery:"))
                        convert_to_money_and_add(800, number + 1, 4, self.ordertable)
                        withdelivery = summedcost + deliverycost
                        convert_to_money_and_add(withdelivery, number + 1, 5, self.ordertable)
                    withdelivery = summedcost + deliverycost
                    if withdelivery >= 10000 or self.loyalty:
                        self.ordertable.insertRow(number + 2 + self.delivery)
                        self.discount = int(withdelivery * 0.05)
                        convert_to_money_and_add(self.discount, number + 1 + self.delivery, 4, self.ordertable, True)
                        self.ordertable.setItem(number + 1 + self.delivery, 3, QTableWidgetItem("Discount:"))
                        self.subcost = withdelivery - self.discount
                        convert_to_money_and_add(self.subcost, number + 1 + self.delivery, 5, self.ordertable)
                        self.gst = int(self.subcost / 10)
                        convert_to_money_and_add(self.gst, number + 2 + self.delivery, 4, self.ordertable)
                        self.ordertable.setItem(number + 2 + self.delivery, 3, QTableWidgetItem("GST:"))
                        self.finalcost = self.subcost + self.gst
                        convert_to_money_and_add(self.finalcost, number + 2 + self.delivery, 5, self.ordertable)
                    else:
                        self.ordertable.removeRow(number + 2 + self.delivery)
                        self.subcost = withdelivery
                        self.gst = int(self.subcost / 10)
                        convert_to_money_and_add(self.gst, number + 1 + self.delivery, 4, self.ordertable)
                        self.ordertable.setItem(number + 1 + deliverycost, 3, QTableWidgetItem("GST:"))
                        self.finalcost = self.subcost + self.gst
                        convert_to_money_and_add(self.finalcost, number + 1 + self.delivery, 5, self.ordertable)
        else:
            self.ordertable.clearContents()
            self.ordertable.setRowCount(0)

    def keyPressEvent(self, event):
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)

class Profile(QDialog): # Profile page
    def __init__(self):
        super(Profile, self).__init__()
        loadUi("profile.ui", self)  # Load the UI file for the profile dialog
        main.setWindowTitle("Profile")  # Set the title of the main window
        program = Program()  # Initialize an instance of the Program class
        self.loyalty = program.loyalty  # Get loyalty status from the Program instance
        if self.loyalty:  # Check if the user has a loyalty card
            self.loyaltytext.setText("Loyalty Card Holder")  # Display loyalty card holder text
        else:
            self.loyaltytext.setText("")  # Clear the loyalty card text
        logins = LoginScreen()  # Initialize an instance of the LoginScreen class
        self.username.setText(logins.user)  # Set the username text to the current user
        conn = sqlite3.connect("cs.db")  # Connect to the SQLite database
        cur = conn.cursor()  # Create a cursor object
        cur.execute('SELECT * FROM orders WHERE username = "'+logins.user+'"')  # Fetch orders for the current user
        orders = cur.fetchall()  # Fetch all orders for the current user

        # Configure return button style and connect to returnmain method
        self.returnbutton.setStyleSheet("""QPushButton {
                border-image: url(./images/assets/return.png) 0 0 0 0 stretch stretch;}""")
        self.returnbutton.clicked.connect(self.returnmain)

        # Connect logout button click event to logout method
        self.logoutbutton.clicked.connect(self.logout)

        # Configure orderstable properties
        self.orderstable.setColumnCount(7)
        self.orderstable.setRowCount(0)
        self.orderstable.setHorizontalHeaderLabels(["Order ID", "Pizza ID", "Pizza", "Cost", "Quantity", "Subtotal", "Order Total"])
        self.orderstable.verticalHeader().setVisible(False)
        self.orderstable.setColumnWidth(0, 60)
        self.orderstable.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.orderstable.setColumnWidth(5, 130)
        self.orderstable.setColumnWidth(6, 130)
        self.orderstable.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rows = 0
        self.rowids = {}

        # Iterate over orders to populate orderstable
        for order in orders:
            self.rowids[order[0]] = self.rows
            orderlist = eval(order[2])
            self.rows += len(orderlist)
            self.rows += 2
            self.rows += order[-1]
            self.orderstable.setRowCount(self.rows)
        
        for order in orders:
            self.orderstable.setItem(self.rowids[order[0]], 0, QTableWidgetItem(str(order[0])))
            orderlist = eval(order[2])
            delivery = order[-1]
            for rows, data in enumerate(orderlist):
                for columns, fields in enumerate(data):
                    value = fields
                    if columns in [2, 4]:
                        value = f"${str(value)[:-2]}.{str(value)[-2:]}"                        
                    self.orderstable.setItem(self.rowids[order[0]]+rows, columns+1, QTableWidgetItem(str(value)))
            summedtotal = 0
            discount = 0
            correctrow = self.rowids[order[0]]+len(orderlist)
            for items in orderlist:
                summedtotal += items[4]  
            convert_to_money_and_add(summedtotal,  correctrow-1, 6, self.orderstable)
            withdelivery = summedtotal + 800*delivery
            if delivery:
                correctrow += 1
                self.orderstable.setItem(correctrow-1, 4, QTableWidgetItem("Delivery:"))
                convert_to_money_and_add(800, correctrow-1, 5, self.orderstable)
                convert_to_money_and_add(withdelivery, correctrow-1, 6, self.orderstable)
            if withdelivery >= 100:
                discount = int(withdelivery*0.05)
            self.orderstable.setItem(correctrow, 4, QTableWidgetItem("Discount:"))
            convert_to_money_and_add(discount, correctrow, 5, self.orderstable, True)
            subtotal = withdelivery - discount
            convert_to_money_and_add(subtotal, correctrow, 6, self.orderstable)
            gst = int(subtotal/10)
            self.orderstable.setItem(correctrow+1, 4, QTableWidgetItem("GST:"))
            convert_to_money_and_add(gst, correctrow+1, 5, self.orderstable)
            total = subtotal+gst
            convert_to_money_and_add(total, correctrow+1, 6, self.orderstable)
            
    def returnmain(self):
        # Return to the main window
        main = Program()
        widget.addWidget(main)
        widget.setCurrentIndex(widget.currentIndex()+1)
    
    def logout(self):
        # Logout the user
        log_event(f"User '{LoginScreen().user}' logged out.")
        LoginScreen().user = ""
        main.setWindowTitle("PapaPizza")
        widget.addWidget(home)
        widget.setCurrentIndex(widget.currentIndex()+1)

    def keyPressEvent(self, event):
        # Handle key press events
        match event.key():
            case QtCore.Qt.Key_Escape:
                pass
            case _:
                super().keyPressEvent(event)

# Create a QApplication instance
app = QApplication(sys.argv)

# Set the application style to Fusion
QApplication.setStyle(QStyleFactory.create("Fusion"))

# Create a HomeScreen instance
home = HomeScreen()

# Create a QStackedWidget instance and add the HomeScreen to it
widget = QStackedWidget()
widget.addWidget(home)

# Set fixed height and width for the widget
widget.setFixedHeight(576)
widget.setFixedWidth(1024)

# Create a QMainWindow instance
main = QtWidgets.QMainWindow()

# Set the window title
main.setWindowTitle("PapaPizza")

# Set the window icon
icon = QIcon("./images/assets/icon.png")
main.setWindowIcon(icon)

# Set the central widget of the main window to the widget
main.setCentralWidget(widget)

# Show the main window
main.show()

# Execute the application event loop and handle any exceptions
try:
    sys.exit(app.exec())
except:
    # If an exception occurs, process the orders and print a message
    process_orders()
    print("Exiting")
