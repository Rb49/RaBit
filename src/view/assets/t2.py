import customtkinter

# Creating app
app = customtkinter.CTk()
app.grid_rowconfigure(0, weight=1)
app.grid_columnconfigure(0, weight=1)

# Creating Canvas
canvas1 = customtkinter.CTkCanvas(app, highlightthickness=0)
canvas1.grid(row=0, column=0, sticky="nsew")

# Creating Scrollbars
scroll_vertical = customtkinter.CTkScrollbar(app, width=15, command=canvas1.yview)
scroll_vertical.grid(row=0, column=1, sticky="ns")

scroll_horizontal = customtkinter.CTkScrollbar(app, height=15, command=canvas1.xview)
scroll_horizontal.grid(row=1, column=0, sticky="ew")

# Linking the scrollbars to the canvas
canvas1.configure(yscrollcommand=scroll_vertical.set)
canvas1.configure(yscrollcommand=scroll_horizontal.set)

# Creating buttons and placing them in the Canvas
button1 = customtkinter.CTkButton(canvas1, text="Hello!")
button1.grid(row=0, column=0)

button2 = customtkinter.CTkButton(canvas1, text="Hello again!")
button2.grid(row=0, column=1)

app.mainloop()