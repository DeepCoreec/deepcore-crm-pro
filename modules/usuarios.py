"""DeepCore CRM Pro — Panel de gestión de usuarios (multi-usuario)."""
import customtkinter as ctk
from tkinter import messagebox, ttk
import database as db


class GestorUsuarios(ctk.CTkFrame):
    """Panel CRUD de usuarios — solo visible para admins."""

    def __init__(self, parent, C: dict):
        super().__init__(parent, fg_color='transparent')
        self.C = C
        self._build()
        self.cargar()

    def _build(self):
        C = self.C

        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(fill='x', pady=(0, 12))
        ctk.CTkLabel(hdr, text="Gestión de Usuarios",
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=C['heading']).pack(side='left')

        ctk.CTkButton(hdr, text="+ Nuevo usuario", width=140, height=34,
                      corner_radius=8, fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=12, weight='bold'),
                      command=self._nuevo).pack(side='right')

        # Tabla
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('U.Treeview',
                        background=C['surface0'], foreground=C['text'],
                        fieldbackground=C['surface0'], rowheight=32,
                        borderwidth=0, font=('Segoe UI', 11))
        style.configure('U.Treeview.Heading',
                        background=C['mantle'], foreground=C['accent'],
                        font=('Segoe UI', 11, 'bold'), relief='flat')
        style.map('U.Treeview', background=[('selected', C['surface1'])])

        cols = ('nombre', 'username', 'rol', 'estado')
        self._tree = ttk.Treeview(self, columns=cols, show='headings',
                                   style='U.Treeview', selectmode='browse')
        self._tree.heading('nombre',   text='Nombre')
        self._tree.heading('username', text='Usuario')
        self._tree.heading('rol',      text='Rol')
        self._tree.heading('estado',   text='Estado')
        self._tree.column('nombre',   width=220)
        self._tree.column('username', width=160)
        self._tree.column('rol',      width=120)
        self._tree.column('estado',   width=100)
        self._tree.pack(fill='both', expand=True)
        self._tree.bind('<Double-1>', lambda e: self._editar())

        # Botones de acción
        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', pady=(8, 0))

        ctk.CTkButton(btns, text="Editar usuario", width=140, height=34,
                      corner_radius=8, fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=12),
                      command=self._editar).pack(side='left', padx=(0, 8))

        ctk.CTkButton(btns, text="Cambiar contraseña", width=160, height=34,
                      corner_radius=8, fg_color=C['surface1'], hover_color=C['surface2'],
                      text_color=C['text'], font=ctk.CTkFont(size=12),
                      command=self._cambiar_pwd).pack(side='left', padx=(0, 8))

        ctk.CTkButton(btns, text="Activar / Desactivar", width=160, height=34,
                      corner_radius=8, fg_color='transparent', hover_color=C['surface1'],
                      border_width=1, border_color=C['amber'],
                      text_color=C['amber'], font=ctk.CTkFont(size=12),
                      command=self._toggle).pack(side='left')

    def cargar(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for u in db.listar_usuarios():
            estado = 'Activo' if u['activo'] else 'Inactivo'
            nombre = f"{u['nombre']} {u.get('apellido','')}".strip()
            self._tree.insert('', 'end', iid=str(u['id']),
                              values=(nombre, u['username'], u['rol'].capitalize(), estado))

    def _seleccionado(self) -> int | None:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _nuevo(self):
        _FormUsuario(self, self.C, uid=None, on_ok=self.cargar)

    def _editar(self):
        uid = self._seleccionado()
        if not uid:
            messagebox.showinfo("Usuarios", "Selecciona un usuario.", parent=self)
            return
        usuarios = {u['id']: u for u in db.listar_usuarios()}
        u = usuarios.get(uid)
        if u:
            _FormUsuario(self, self.C, uid=uid, datos=u, on_ok=self.cargar)

    def _cambiar_pwd(self):
        uid = self._seleccionado()
        if not uid:
            messagebox.showinfo("Usuarios", "Selecciona un usuario.", parent=self)
            return
        _CambiarPassword(self, self.C, uid=uid)

    def _toggle(self):
        uid = self._seleccionado()
        if not uid:
            messagebox.showinfo("Usuarios", "Selecciona un usuario.", parent=self)
            return
        # No desactivar al único admin activo
        admins = [u for u in db.listar_usuarios() if u['rol'] == 'admin' and u['activo']]
        usuario = next((u for u in db.listar_usuarios() if u['id'] == uid), None)
        if usuario and usuario['rol'] == 'admin' and len(admins) <= 1 and usuario['activo']:
            messagebox.showerror("Usuarios",
                                 "No puedes desactivar el único administrador activo.", parent=self)
            return
        db.toggle_activo_usuario(uid)
        self.cargar()


class _FormUsuario(ctk.CTkToplevel):
    def __init__(self, master, C: dict, uid=None, datos: dict = None, on_ok=None):
        super().__init__(master)
        self.C   = C
        self._uid = uid
        self._on_ok = on_ok
        es_nuevo = uid is None
        self.title("Nuevo usuario" if es_nuevo else "Editar usuario")
        self.geometry("400x440")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()
        self._center()
        self._build(datos or {}, es_nuevo)

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw-400)//2}+{(sh-440)//2}")

    def _build(self, datos: dict, es_nuevo: bool):
        C = self.C
        ctk.CTkFrame(self, fg_color=C['accent'], height=3).pack(fill='x')
        ctk.CTkLabel(self, text="Nuevo usuario" if es_nuevo else "Editar usuario",
                     font=ctk.CTkFont(size=16, weight='bold'),
                     text_color=C['heading']).pack(pady=(16, 4))
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=8)

        def campo(label, valor='', show=''):
            ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=11),
                         text_color=C['text2']).pack(anchor='w', padx=24)
            e = ctk.CTkEntry(self, width=352, height=36, corner_radius=8,
                             fg_color=C['surface0'], border_color=C['border'],
                             border_width=1, text_color=C['text'],
                             font=ctk.CTkFont(size=13), show=show)
            if valor:
                e.insert(0, valor)
            e.pack(padx=24, pady=(2, 8))
            return e

        self._e_nombre   = campo("Nombre", datos.get('nombre', ''))
        self._e_apellido = campo("Apellido", datos.get('apellido', ''))
        self._e_username = campo("Usuario (para login)", datos.get('username', ''))
        if es_nuevo:
            self._e_password = campo("Contraseña", show='*')
        else:
            self._e_password = None

        ctk.CTkLabel(self, text="Rol", font=ctk.CTkFont(size=11),
                     text_color=C['text2']).pack(anchor='w', padx=24)
        self._combo_rol = ctk.CTkComboBox(
            self, values=['admin', 'vendedor'], width=352, height=36, corner_radius=8,
            fg_color=C['surface0'], border_color=C['border'],
            button_color=C['accent'], dropdown_fg_color=C['surface0'],
            text_color=C['text'], font=ctk.CTkFont(size=13))
        self._combo_rol.set(datos.get('rol', 'vendedor'))
        self._combo_rol.pack(padx=24, pady=(2, 16))

        ctk.CTkButton(self, text="Guardar", width=200, height=40,
                      corner_radius=8, fg_color=C['green'], hover_color=C['teal'],
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._guardar).pack(pady=(0, 12))

    def _guardar(self):
        nombre   = self._e_nombre.get().strip()
        apellido = self._e_apellido.get().strip()
        username = self._e_username.get().strip().lower()
        rol      = self._combo_rol.get()

        if not nombre or not username:
            messagebox.showerror("Error", "Nombre y usuario son obligatorios.", parent=self)
            return

        if self._uid is None:
            pwd = self._e_password.get().strip() if self._e_password else ''
            if not pwd:
                messagebox.showerror("Error", "La contraseña es obligatoria.", parent=self)
                return
            try:
                db.crear_usuario(nombre, apellido, username, pwd, rol)
            except Exception as e:
                messagebox.showerror("Error", f"El usuario ya existe o hay un error:\n{e}", parent=self)
                return
        else:
            db.actualizar_usuario(self._uid, nombre, apellido, rol)

        if self._on_ok:
            self._on_ok()
        self.destroy()


class _CambiarPassword(ctk.CTkToplevel):
    def __init__(self, master, C: dict, uid: int):
        super().__init__(master)
        self.C   = C
        self._uid = uid
        self.title("Cambiar contraseña")
        self.geometry("360x280")
        self.configure(fg_color=C['base'])
        self.resizable(False, False)
        self.grab_set()
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw-360)//2}+{(sh-280)//2}")
        self._build()

    def _build(self):
        C = self.C
        ctk.CTkFrame(self, fg_color=C['amber'], height=3).pack(fill='x')
        ctk.CTkLabel(self, text="Cambiar contraseña",
                     font=ctk.CTkFont(size=15, weight='bold'),
                     text_color=C['heading']).pack(pady=(16, 4))
        ctk.CTkFrame(self, fg_color=C['border'], height=1).pack(fill='x', padx=24, pady=8)

        ctk.CTkLabel(self, text="Nueva contraseña", font=ctk.CTkFont(size=11),
                     text_color=C['text2']).pack(anchor='w', padx=24)
        self._e1 = ctk.CTkEntry(self, width=312, height=36, corner_radius=8,
                                fg_color=C['surface0'], border_color=C['border'],
                                border_width=1, text_color=C['text'],
                                font=ctk.CTkFont(size=13), show='*')
        self._e1.pack(padx=24, pady=(2, 8))

        ctk.CTkLabel(self, text="Confirmar contraseña", font=ctk.CTkFont(size=11),
                     text_color=C['text2']).pack(anchor='w', padx=24)
        self._e2 = ctk.CTkEntry(self, width=312, height=36, corner_radius=8,
                                fg_color=C['surface0'], border_color=C['border'],
                                border_width=1, text_color=C['text'],
                                font=ctk.CTkFont(size=13), show='*')
        self._e2.pack(padx=24, pady=(2, 16))

        ctk.CTkButton(self, text="Cambiar", width=180, height=38,
                      corner_radius=8, fg_color=C['amber'], hover_color='#f59e0b',
                      text_color='#000000', font=ctk.CTkFont(size=13, weight='bold'),
                      command=self._guardar).pack()

    def _guardar(self):
        p1 = self._e1.get().strip()
        p2 = self._e2.get().strip()
        if not p1:
            messagebox.showerror("Error", "La contraseña no puede estar vacía.", parent=self)
            return
        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self)
            return
        db.cambiar_password(self._uid, p1)
        messagebox.showinfo("Listo", "Contraseña cambiada correctamente.", parent=self)
        self.destroy()
