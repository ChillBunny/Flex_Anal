import math
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# corre analizador.exe con el texto y devuelve la lista de tokens
def analizar_texto(texto):
    # si la app esta empaquetada con pyinstaller, analizador.exe viene adentro
    # del ejecutable y se descomprime en la carpeta sys._MEIPASS
    if getattr(sys, "frozen", False):
        carpeta = sys._MEIPASS
    else:
        carpeta = os.path.dirname(os.path.abspath(__file__))
    ruta_analizador = os.path.join(carpeta, "analizador.exe")

    if not os.path.exists(ruta_analizador):
        messagebox.showerror("Error", "No se encontró analizador.exe.\nPrimero hay que correr compilar.bat")
        return []

    # CREATE_NO_WINDOW es para que no se abra una ventana negra de consola
    resultado = subprocess.run(
        [ruta_analizador],
        input=texto.encode("utf-8"),
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    salida = resultado.stdout.decode("utf-8", errors="replace")

    tokens = []
    for linea in salida.splitlines():
        # cada linea viene asi: TOKEN <tab> lexema <tab> linea <tab> columna
        # un comentario puede traer tabs adentro, por eso se parte por los dos lados
        token, resto = linea.split("\t", 1)
        lexema, numero_linea, columna = resto.rsplit("\t", 2)
        tokens.append((token, lexema, int(numero_linea), int(columna)))
    return tokens


# boton Analizar
def analizar():
    texto = editor.get("1.0", "end-1c")
    tokens = analizar_texto(texto)
    llenar_tabla_tokens(tokens)
    llenar_tabla_simbolos(tokens)
    marcar_errores(tokens)
    mostrar_resumen(tokens)


def llenar_tabla_tokens(tokens):
    tabla_tokens.delete(*tabla_tokens.get_children())
    numero = 1
    for token, lexema, linea, columna in tokens:
        if token == "ERROR":
            tabla_tokens.insert("", "end", values=(numero, token, lexema, linea, columna), tags=("error",))
        else:
            tabla_tokens.insert("", "end", values=(numero, token, lexema, linea, columna))
        numero = numero + 1


# cada identificador una sola vez, con la linea donde aparece
# por primera vez y cuantas veces aparece en total
def llenar_tabla_simbolos(tokens):
    tabla_simbolos.delete(*tabla_simbolos.get_children())
    primera_linea = {}
    apariciones = {}
    for token, lexema, linea, columna in tokens:
        if token == "IDENTIFICADOR":
            if lexema not in primera_linea:
                primera_linea[lexema] = linea
                apariciones[lexema] = 0
            apariciones[lexema] = apariciones[lexema] + 1

    for nombre in primera_linea:
        tabla_simbolos.insert("", "end", values=(nombre, primera_linea[nombre], apariciones[nombre]))


# pinta de rojo en el editor lo que dio error
def marcar_errores(tokens):
    editor.tag_remove("error", "1.0", "end")
    for token, lexema, linea, columna in tokens:
        if token == "ERROR":
            # en tkinter las columnas empiezan en 0 y en el analizador en 1
            inicio = f"{linea}.{columna - 1}"
            fin = f"{linea}.{columna - 1 + len(lexema)}"
            editor.tag_add("error", inicio, fin)


def mostrar_resumen(tokens):
    errores = 0
    for token, lexema, linea, columna in tokens:
        if token == "ERROR":
            errores = errores + 1
    correctos = len(tokens) - errores

    if errores == 0:
        etiqueta_resumen.config(text=f"{correctos} tokens reconocidos, sin errores léxicos", foreground="dark green")
    else:
        etiqueta_resumen.config(text=f"{correctos} tokens reconocidos y {errores} errores léxicos", foreground="red")


def abrir_archivo():
    ruta = filedialog.askopenfilename(filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")])
    if ruta == "":
        return
    with open(ruta, encoding="utf-8", errors="replace") as archivo:
        contenido = archivo.read()
    editor.delete("1.0", "end")
    editor.insert("1.0", contenido)
    analizar()


def limpiar():
    editor.delete("1.0", "end")
    editor.tag_remove("error", "1.0", "end")
    tabla_tokens.delete(*tabla_tokens.get_children())
    tabla_simbolos.delete(*tabla_simbolos.get_children())
    etiqueta_resumen.config(text="")


# ---------------------------------------------------------------------------------------------
# dibujo del automata

RADIO = 18


def dibujar_estado(lienzo, x, y, numero, acepta):
    lienzo.create_oval(x - RADIO, y - RADIO, x + RADIO, y + RADIO, width=2, fill="white")
    # los estados de aceptacion llevan doble circulo
    if acepta:
        lienzo.create_oval(x - RADIO + 4, y - RADIO + 4, x + RADIO - 4, y + RADIO - 4, width=1)
    lienzo.create_text(x, y, text=str(numero), font=("Segoe UI", 10, "bold"))


# flecha de un estado a otro. la etiqueta va encima de la misma flecha,
# con fondo blanco, para que se sepa de cual flecha es
def dibujar_flecha(lienzo, x1, y1, x2, y2, etiqueta):
    distancia = math.hypot(x2 - x1, y2 - y1)
    dx = (x2 - x1) / distancia
    dy = (y2 - y1) / distancia
    inicio_x = x1 + dx * RADIO
    inicio_y = y1 + dy * RADIO
    fin_x = x2 - dx * RADIO
    fin_y = y2 - dy * RADIO
    lienzo.create_line(inicio_x, inicio_y, fin_x, fin_y, arrow=tk.LAST, width=1.5)

    # si la flecha es horizontal, la etiqueta va arriba de la linea
    if y1 == y2:
        lienzo.create_text((inicio_x + fin_x) / 2, inicio_y - 10, text=etiqueta, font=("Consolas", 9), fill="blue")
        return

    texto_x = inicio_x + (fin_x - inicio_x) * 0.78
    texto_y = inicio_y + (fin_y - inicio_y) * 0.78
    texto = lienzo.create_text(texto_x, texto_y, text=etiqueta, font=("Consolas", 9), fill="blue")
    fondo = lienzo.create_rectangle(lienzo.bbox(texto), fill="white", outline="")
    lienzo.tag_lower(fondo, texto)


# flecha que sale y vuelve al mismo estado, por arriba
def dibujar_lazo_arriba(lienzo, x, y, etiqueta):
    puntos = [x - 8, y - RADIO, x - 16, y - RADIO - 24, x + 16, y - RADIO - 24, x + 8, y - RADIO]
    lienzo.create_line(puntos, smooth=True, arrow=tk.LAST, width=1.5)
    lienzo.create_text(x, y - RADIO - 32, text=etiqueta, font=("Consolas", 9), fill="blue")


# flecha que sale y vuelve al mismo estado, por la derecha
def dibujar_lazo_derecha(lienzo, x, y, etiqueta):
    puntos = [x + RADIO, y - 8, x + RADIO + 24, y - 16, x + RADIO + 24, y + 16, x + RADIO, y + 8]
    lienzo.create_line(puntos, smooth=True, arrow=tk.LAST, width=1.5)
    lienzo.create_text(x + RADIO + 30, y, text=etiqueta, font=("Consolas", 9), fill="blue", anchor="w")


def dibujar_token(lienzo, y, nombre):
    lienzo.create_text(525, y, text=nombre, font=("Segoe UI", 10, "bold"), anchor="w")


def dibujar_automata(lienzo):
    lienzo.create_text(20, 20, text="Autómata finito determinista del analizador", font=("Segoe UI", 12, "bold"), anchor="w")

    # estado inicial
    x0 = 60
    y0 = 328
    lienzo.create_line(5, y0, x0 - RADIO, y0, arrow=tk.LAST, width=1.5)
    lienzo.create_text(22, y0 - 12, text="inicio", font=("Segoe UI", 9))
    dibujar_estado(lienzo, x0, y0, 0, False)

    x = 300

    # numeros: enteros y decimales
    dibujar_estado(lienzo, x, 95, 1, True)
    dibujar_estado(lienzo, 385, 95, 2, False)
    dibujar_estado(lienzo, 470, 95, 3, True)
    dibujar_flecha(lienzo, x0, y0, x, 95, "dígito")
    dibujar_lazo_arriba(lienzo, x, 95, "dígito")
    dibujar_flecha(lienzo, x, 95, 385, 95, ".")
    dibujar_flecha(lienzo, 385, 95, 470, 95, "dígito")
    dibujar_lazo_arriba(lienzo, 470, 95, "dígito")
    dibujar_token(lienzo, 95, "NUMERO")

    # identificadores
    dibujar_estado(lienzo, x, 145, 4, True)
    dibujar_flecha(lienzo, x0, y0, x, 145, "letra o _")
    dibujar_lazo_derecha(lienzo, x, 145, "letra, dígito o _")
    dibujar_token(lienzo, 145, "IDENTIFICADOR")

    # comentarios
    dibujar_estado(lienzo, x, 190, 5, True)
    dibujar_flecha(lienzo, x0, y0, x, 190, "#")
    dibujar_lazo_derecha(lienzo, x, 190, "todo menos salto")
    dibujar_token(lienzo, 190, "COMENTARIO")

    # operadores y parentesis, un estado para cada uno
    dibujar_estado(lienzo, x, 232, 6, True)
    dibujar_flecha(lienzo, x0, y0, x, 232, "=")
    dibujar_token(lienzo, 232, "ASIGNACION")

    dibujar_estado(lienzo, x, 272, 7, True)
    dibujar_flecha(lienzo, x0, y0, x, 272, "+")
    dibujar_token(lienzo, 272, "SUMA")

    dibujar_estado(lienzo, x, 312, 8, True)
    dibujar_flecha(lienzo, x0, y0, x, 312, "-")
    dibujar_token(lienzo, 312, "RESTA")

    dibujar_estado(lienzo, x, 352, 9, True)
    dibujar_flecha(lienzo, x0, y0, x, 352, "*")
    dibujar_token(lienzo, 352, "MULT")

    dibujar_estado(lienzo, x, 392, 10, True)
    dibujar_flecha(lienzo, x0, y0, x, 392, "/")
    dibujar_token(lienzo, 392, "DIV")

    dibujar_estado(lienzo, x, 432, 11, True)
    dibujar_flecha(lienzo, x0, y0, x, 432, "(")
    dibujar_token(lienzo, 432, "PAR_IZQ")

    dibujar_estado(lienzo, x, 472, 12, True)
    dibujar_flecha(lienzo, x0, y0, x, 472, ")")
    dibujar_token(lienzo, 472, "PAR_DER")

    # espacios en blanco, no devuelven token
    dibujar_estado(lienzo, x, 515, 13, True)
    dibujar_flecha(lienzo, x0, y0, x, 515, "espacio")
    dibujar_lazo_derecha(lienzo, x, 515, "espacio, tab, \\n")
    dibujar_token(lienzo, 515, "(se descarta)")

    # cualquier otro caracter
    dibujar_estado(lienzo, x, 560, 14, True)
    dibujar_flecha(lienzo, x0, y0, x, 560, "otro")
    dibujar_token(lienzo, 560, "ERROR")

    nota = ("Doble círculo = estado de aceptación.\n"
            "El estado 2 no acepta: con \"3.\" el analizador llega ahí, no puede seguir y regresa\n"
            "al último estado que aceptó (el 1). Devuelve NUMERO \"3\" y el punto queda como ERROR.")
    lienzo.create_text(20, 595, text=nota, font=("Segoe UI", 9), anchor="nw", justify="left")


# ---------------------------------------------------------------------------------------------
# ventana principal

def crear_ventana():
    global editor, tabla_tokens, tabla_simbolos, etiqueta_resumen

    ventana = tk.Tk()
    ventana.title("Analizador léxico - Calculadora con variables")
    ventana.geometry("1200x700")

    # barra de arriba con los botones
    barra = ttk.Frame(ventana, padding=8)
    barra.pack(fill="x")
    ttk.Label(barra, text="Analizador léxico", font=("Segoe UI", 14, "bold")).pack(side="left")
    ttk.Label(barra, text="   F5 = analizar", foreground="gray").pack(side="left")
    ttk.Button(barra, text="Limpiar", command=limpiar).pack(side="right", padx=4)
    ttk.Button(barra, text="Analizar", command=analizar).pack(side="right", padx=4)
    ttk.Button(barra, text="Abrir archivo", command=abrir_archivo).pack(side="right", padx=4)

    # abajo, el resumen del analisis
    etiqueta_resumen = ttk.Label(ventana, text="", padding=8, font=("Segoe UI", 10, "bold"))
    etiqueta_resumen.pack(side="bottom", fill="x")

    # en medio, el editor a la izquierda y las pestañas a la derecha
    panel = ttk.PanedWindow(ventana, orient="horizontal")
    panel.pack(fill="both", expand=True, padx=8)

    marco_editor = ttk.LabelFrame(panel, text="Código fuente", padding=4)
    editor = tk.Text(marco_editor, font=("Consolas", 12), undo=True, wrap="none", width=45)
    barra_editor = ttk.Scrollbar(marco_editor, command=editor.yview)
    editor.config(yscrollcommand=barra_editor.set)
    barra_editor.pack(side="right", fill="y")
    editor.pack(fill="both", expand=True)
    editor.tag_config("error", background="#ffb3b3")
    panel.add(marco_editor, weight=2)

    pestanas = ttk.Notebook(panel)
    panel.add(pestanas, weight=3)

    # pestaña de tokens
    marco_tokens = ttk.Frame(pestanas)
    columnas = ("numero", "token", "lexema", "linea", "columna")
    tabla_tokens = ttk.Treeview(marco_tokens, columns=columnas, show="headings")
    tabla_tokens.heading("numero", text="#")
    tabla_tokens.heading("token", text="Token")
    tabla_tokens.heading("lexema", text="Lexema")
    tabla_tokens.heading("linea", text="Línea")
    tabla_tokens.heading("columna", text="Columna")
    tabla_tokens.column("numero", width=40, anchor="center")
    tabla_tokens.column("token", width=140)
    tabla_tokens.column("lexema", width=260)
    tabla_tokens.column("linea", width=60, anchor="center")
    tabla_tokens.column("columna", width=70, anchor="center")
    tabla_tokens.tag_configure("error", background="#ffb3b3")
    barra_tokens = ttk.Scrollbar(marco_tokens, command=tabla_tokens.yview)
    tabla_tokens.config(yscrollcommand=barra_tokens.set)
    barra_tokens.pack(side="right", fill="y")
    tabla_tokens.pack(fill="both", expand=True)
    pestanas.add(marco_tokens, text="Tokens")

    # pestaña de la tabla de simbolos
    marco_simbolos = ttk.Frame(pestanas)
    tabla_simbolos = ttk.Treeview(marco_simbolos, columns=("nombre", "linea", "veces"), show="headings")
    tabla_simbolos.heading("nombre", text="Identificador")
    tabla_simbolos.heading("linea", text="Primera línea")
    tabla_simbolos.heading("veces", text="Apariciones")
    tabla_simbolos.column("nombre", width=220)
    tabla_simbolos.column("linea", width=110, anchor="center")
    tabla_simbolos.column("veces", width=110, anchor="center")
    tabla_simbolos.pack(fill="both", expand=True)
    pestanas.add(marco_simbolos, text="Tabla de símbolos")

    # pestaña del automata, con barra por si la ventana es chica
    marco_automata = ttk.Frame(pestanas)
    lienzo = tk.Canvas(marco_automata, background="white", scrollregion=(0, 0, 720, 650))
    barra_automata = ttk.Scrollbar(marco_automata, command=lienzo.yview)
    lienzo.config(yscrollcommand=barra_automata.set)
    barra_automata.pack(side="right", fill="y")
    lienzo.pack(fill="both", expand=True)
    dibujar_automata(lienzo)
    pestanas.add(marco_automata, text="Autómata")

    ventana.bind("<F5>", lambda evento: analizar())

    # un ejemplo para que no arranque vacio
    editor.insert("1.0", "# precio con descuento\n"
                         "precio = 150.50\n"
                         "descuento = 0.15\n"
                         "total = precio - (precio * descuento)\n")
    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.state("zoomed")
    ventana.after(100, analizar)
    ventana.mainloop()
