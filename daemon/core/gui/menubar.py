import logging
import os
import tkinter as tk
import webbrowser
from functools import partial
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from core.gui.appconfig import XMLS_PATH
from core.gui.coreclient import OBSERVERS
from core.gui.dialogs.about import AboutDialog
from core.gui.dialogs.canvassizeandscale import SizeAndScaleDialog
from core.gui.dialogs.canvaswallpaper import CanvasWallpaperDialog
from core.gui.dialogs.executepython import ExecutePythonDialog
from core.gui.dialogs.hooks import HooksDialog
from core.gui.dialogs.observers import ObserverDialog
from core.gui.dialogs.preferences import PreferencesDialog
from core.gui.dialogs.servers import ServersDialog
from core.gui.dialogs.sessionoptions import SessionOptionsDialog
from core.gui.dialogs.sessions import SessionsDialog
from core.gui.dialogs.throughput import ThroughputDialog
from core.gui.nodeutils import ICON_SIZE
from core.gui.task import BackgroundTask

if TYPE_CHECKING:
    from core.gui.app import Application

MAX_FILES = 3


class Menubar(tk.Menu):
    """
    Core menubar
    """

    def __init__(self, master: tk.Tk, app: "Application", **kwargs) -> None:
        """
        Create a CoreMenubar instance
        """
        super().__init__(master, **kwargs)
        self.master.config(menu=self)
        self.app = app
        self.core = app.core
        self.canvas = app.canvas
        self.recent_menu = None
        self.edit_menu = None
        self.draw()

    def draw(self) -> None:
        """
        Create core menubar and bind the hot keys to their matching command
        """
        self.draw_file_menu()
        self.draw_edit_menu()
        self.draw_canvas_menu()
        self.draw_view_menu()
        self.draw_tools_menu()
        self.draw_widgets_menu()
        self.draw_session_menu()
        self.draw_help_menu()

    def draw_file_menu(self) -> None:
        """
        Create file menu
        """
        menu = tk.Menu(self)
        menu.add_command(
            label="New Session", accelerator="Ctrl+N", command=self.click_new
        )
        self.app.bind_all("<Control-n>", lambda e: self.click_new())
        menu.add_command(label="Save", accelerator="Ctrl+S", command=self.click_save)
        self.app.bind_all("<Control-s>", self.click_save)
        menu.add_command(label="Save As...", command=self.click_save_xml)
        menu.add_command(
            label="Open...", command=self.click_open_xml, accelerator="Ctrl+O"
        )
        self.app.bind_all("<Control-o>", self.click_open_xml)
        self.recent_menu = tk.Menu(menu)
        for i in self.app.guiconfig["recentfiles"]:
            self.recent_menu.add_command(
                label=i, command=partial(self.open_recent_files, i)
            )
        menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        menu.add_separator()
        menu.add_command(label="Execute Python Script...", command=self.execute_python)
        menu.add_separator()
        menu.add_command(
            label="Quit",
            accelerator="Ctrl+Q",
            command=lambda: self.prompt_save_running_session(True),
        )
        self.app.bind_all(
            "<Control-q>", lambda _: self.prompt_save_running_session(True)
        )
        self.add_cascade(label="File", menu=menu)

    def draw_edit_menu(self) -> None:
        """
        Create edit menu
        """
        menu = tk.Menu(self)
        menu.add_command(label="Preferences", command=self.click_preferences)
        menu.add_command(label="Undo", accelerator="Ctrl+Z", state=tk.DISABLED)
        menu.add_command(label="Redo", accelerator="Ctrl+Y", state=tk.DISABLED)
        menu.add_separator()
        menu.add_command(label="Cut", accelerator="Ctrl+X", command=self.click_cut)
        menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.click_copy)
        menu.add_command(label="Paste", accelerator="Ctrl+V", command=self.click_paste)
        menu.add_command(
            label="Delete", accelerator="Ctrl+D", command=self.click_delete
        )
        self.add_cascade(label="Edit", menu=menu)
        self.app.master.bind_all("<Control-x>", self.click_cut)
        self.app.master.bind_all("<Control-c>", self.click_copy)
        self.app.master.bind_all("<Control-v>", self.click_paste)
        self.app.master.bind_all("<Control-d>", self.click_delete)
        self.edit_menu = menu

    def draw_canvas_menu(self) -> None:
        """
        Create canvas menu
        """
        menu = tk.Menu(self)
        menu.add_command(label="Size / Scale", command=self.click_canvas_size_and_scale)
        menu.add_command(label="Wallpaper", command=self.click_canvas_wallpaper)
        self.add_cascade(label="Canvas", menu=menu)

    def draw_view_menu(self) -> None:
        """
        Create view menu
        """
        menu = tk.Menu(self)
        menu.add_checkbutton(
            label="Interface Names",
            command=self.click_edge_label_change,
            variable=self.canvas.show_interface_names,
        )
        menu.add_checkbutton(
            label="IPv4 Addresses",
            command=self.click_edge_label_change,
            variable=self.canvas.show_ip4s,
        )
        menu.add_checkbutton(
            label="IPv6 Addresses",
            command=self.click_edge_label_change,
            variable=self.canvas.show_ip6s,
        )
        menu.add_checkbutton(
            label="Node Labels",
            command=self.canvas.show_node_labels.click_handler,
            variable=self.canvas.show_node_labels,
        )
        menu.add_checkbutton(
            label="Link Labels",
            command=self.canvas.show_link_labels.click_handler,
            variable=self.canvas.show_link_labels,
        )
        menu.add_checkbutton(
            label="Annotations",
            command=self.canvas.show_annotations.click_handler,
            variable=self.canvas.show_annotations,
        )
        menu.add_checkbutton(
            label="Canvas Grid",
            command=self.canvas.show_grid.click_handler,
            variable=self.canvas.show_grid,
        )
        self.add_cascade(label="View", menu=menu)

    def draw_tools_menu(self) -> None:
        """
        Create tools menu
        """
        menu = tk.Menu(self)
        menu.add_command(label="Auto Grid", command=self.click_autogrid)
        menu.add_command(label="IP Addresses", state=tk.DISABLED)
        menu.add_command(label="MAC Addresses", state=tk.DISABLED)
        self.add_cascade(label="Tools", menu=menu)

    def create_observer_widgets_menu(self, widget_menu: tk.Menu) -> None:
        """
        Create observer widget menu item and create the sub menu items inside
        """
        var = tk.StringVar(value="none")
        menu = tk.Menu(widget_menu)
        menu.var = var
        menu.add_command(
            label="Edit Observers", command=self.click_edit_observer_widgets
        )
        menu.add_separator()
        menu.add_radiobutton(
            label="None",
            variable=var,
            value="none",
            command=lambda: self.core.set_observer(None),
        )
        for name in sorted(OBSERVERS):
            cmd = OBSERVERS[name]
            menu.add_radiobutton(
                label=name,
                variable=var,
                value=name,
                command=partial(self.core.set_observer, cmd),
            )
        for name in sorted(self.core.custom_observers):
            observer = self.core.custom_observers[name]
            menu.add_radiobutton(
                label=name,
                variable=var,
                value=name,
                command=partial(self.core.set_observer, observer.cmd),
            )
        widget_menu.add_cascade(label="Observer Widgets", menu=menu)

    def create_adjacency_menu(self, widget_menu: tk.Menu) -> None:
        """
        Create adjacency menu item and the sub menu items inside
        """
        menu = tk.Menu(widget_menu)
        menu.add_command(label="Configure Adjacency", state=tk.DISABLED)
        menu.add_command(label="Enable OSPFv2?", state=tk.DISABLED)
        menu.add_command(label="Enable OSPFv3?", state=tk.DISABLED)
        menu.add_command(label="Enable OSLR?", state=tk.DISABLED)
        menu.add_command(label="Enable OSLRv2?", state=tk.DISABLED)
        widget_menu.add_cascade(label="Adjacency", menu=menu)

    def create_throughput_menu(self, widget_menu: tk.Menu) -> None:
        menu = tk.Menu(widget_menu)
        menu.add_command(
            label="Configure Throughput", command=self.click_config_throughput
        )
        menu.add_checkbutton(label="Enable Throughput?", command=self.click_throughput)
        widget_menu.add_cascade(label="Throughput", menu=menu)

    def draw_widgets_menu(self) -> None:
        """
        Create widget menu
        """
        menu = tk.Menu(self)
        self.create_observer_widgets_menu(menu)
        self.create_adjacency_menu(menu)
        self.create_throughput_menu(menu)
        self.add_cascade(label="Widgets", menu=menu)

    def draw_session_menu(self) -> None:
        """
        Create session menu
        """
        menu = tk.Menu(self)
        menu.add_command(label="Sessions", command=self.click_sessions)
        menu.add_command(label="Servers", command=self.click_servers)
        menu.add_command(label="Options", command=self.click_session_options)
        menu.add_command(label="Hooks", command=self.click_hooks)
        self.add_cascade(label="Session", menu=menu)

    def draw_help_menu(self) -> None:
        """
        Create help menu
        """
        menu = tk.Menu(self)
        menu.add_command(label="Core GitHub (www)", command=self.click_core_github)
        menu.add_command(label="Core Documentation (www)", command=self.click_core_doc)
        menu.add_command(label="About", command=self.click_about)
        self.add_cascade(label="Help", menu=menu)

    def open_recent_files(self, filename: str) -> None:
        if os.path.isfile(filename):
            logging.debug("Open recent file %s", filename)
            self.open_xml_task(filename)
        else:
            logging.warning("File does not exist %s", filename)

    def update_recent_files(self) -> None:
        self.recent_menu.delete(0, tk.END)
        for i in self.app.guiconfig["recentfiles"]:
            self.recent_menu.add_command(
                label=i, command=partial(self.open_recent_files, i)
            )

    def click_save(self, _event=None) -> None:
        xml_file = self.core.xml_file
        if xml_file:
            self.core.save_xml(xml_file)
        else:
            self.click_save_xml()

    def click_save_xml(self, _event: tk.Event = None) -> None:
        init_dir = self.core.xml_dir
        if not init_dir:
            init_dir = str(XMLS_PATH)
        file_path = filedialog.asksaveasfilename(
            initialdir=init_dir,
            title="Save As",
            filetypes=(("XML files", "*.xml"), ("All files", "*")),
            defaultextension=".xml",
        )
        if file_path:
            self.add_recent_file_to_gui_config(file_path)
            self.core.save_xml(file_path)
            self.core.xml_file = file_path

    def click_open_xml(self, _event: tk.Event = None) -> None:
        init_dir = self.core.xml_dir
        if not init_dir:
            init_dir = str(XMLS_PATH)
        file_path = filedialog.askopenfilename(
            initialdir=init_dir,
            title="Open",
            filetypes=(("XML Files", "*.xml"), ("All Files", "*")),
        )
        if file_path:
            self.open_xml_task(file_path)

    def open_xml_task(self, filename: str) -> None:
        self.add_recent_file_to_gui_config(filename)
        self.core.xml_file = filename
        self.core.xml_dir = str(os.path.dirname(filename))
        self.prompt_save_running_session()
        self.app.statusbar.progress_bar.start(5)
        task = BackgroundTask(self.app, self.core.open_xml, args=(filename,))
        task.start()

    def execute_python(self):
        dialog = ExecutePythonDialog(self.app, self.app)
        dialog.show()

    def add_recent_file_to_gui_config(self, file_path) -> None:
        recent_files = self.app.guiconfig["recentfiles"]
        num_files = len(recent_files)
        if num_files == 0:
            recent_files.insert(0, file_path)
        elif 0 < num_files <= MAX_FILES:
            if file_path in recent_files:
                recent_files.remove(file_path)
                recent_files.insert(0, file_path)
            else:
                if num_files == MAX_FILES:
                    recent_files.pop()
                recent_files.insert(0, file_path)
        else:
            logging.error("unexpected number of recent files")
        self.app.save_config()
        self.app.menubar.update_recent_files()

    def change_menubar_item_state(self, is_runtime: bool) -> None:
        labels = {"Copy", "Paste", "Delete", "Cut"}
        for i in range(self.edit_menu.index(tk.END) + 1):
            try:
                label = self.edit_menu.entrycget(i, "label")
                logging.info("menu label: %s", label)
                if label not in labels:
                    continue
                state = tk.DISABLED if is_runtime else tk.NORMAL
                self.edit_menu.entryconfig(i, state=state)
            except tk.TclError:
                pass

    def prompt_save_running_session(self, quit_app: bool = False) -> None:
        """
        Prompt use to stop running session before application is closed

        :param quit_app: True to quit app, False otherwise
        """
        result = True
        if self.core.is_runtime():
            result = messagebox.askyesnocancel("Exit", "Stop the running session?")
        if result:
            callback = None
            if quit_app:
                callback = self.app.quit
            task = BackgroundTask(self.app, self.core.delete_session, callback)
            task.start()
        elif quit_app:
            self.app.quit()

    def click_new(self) -> None:
        self.prompt_save_running_session()
        self.core.create_new_session()
        self.core.xml_file = None

    def click_preferences(self) -> None:
        dialog = PreferencesDialog(self.app, self.app)
        dialog.show()

    def click_canvas_size_and_scale(self) -> None:
        dialog = SizeAndScaleDialog(self.app, self.app)
        dialog.show()

    def click_canvas_wallpaper(self) -> None:
        dialog = CanvasWallpaperDialog(self.app, self.app)
        dialog.show()

    def click_core_github(self) -> None:
        webbrowser.open_new("https://github.com/coreemu/core")

    def click_core_doc(self) -> None:
        webbrowser.open_new("http://coreemu.github.io/core/")

    def click_about(self) -> None:
        dialog = AboutDialog(self.app, self.app)
        dialog.show()

    def click_throughput(self) -> None:
        if not self.core.handling_throughputs:
            self.core.enable_throughputs()
        else:
            self.core.cancel_throughputs()

    def click_config_throughput(self) -> None:
        dialog = ThroughputDialog(self.app, self.app)
        dialog.show()

    def click_copy(self, _event: tk.Event = None) -> None:
        self.canvas.copy()

    def click_paste(self, _event: tk.Event = None) -> None:
        self.canvas.paste()

    def click_delete(self, _event: tk.Event = None) -> None:
        self.canvas.delete_selected_objects()

    def click_cut(self, _event: tk.Event = None) -> None:
        self.canvas.copy()
        self.canvas.delete_selected_objects()

    def click_session_options(self) -> None:
        logging.debug("Click options")
        dialog = SessionOptionsDialog(self.app, self.app)
        if not dialog.has_error:
            dialog.show()

    def click_sessions(self) -> None:
        logging.debug("Click change sessions")
        dialog = SessionsDialog(self.app, self.app)
        dialog.show()

    def click_hooks(self) -> None:
        logging.debug("Click hooks")
        dialog = HooksDialog(self.app, self.app)
        dialog.show()

    def click_servers(self) -> None:
        logging.debug("Click emulation servers")
        dialog = ServersDialog(self.app, self.app)
        dialog.show()

    def click_edit_observer_widgets(self) -> None:
        dialog = ObserverDialog(self.app, self.app)
        dialog.show()

    def click_autogrid(self) -> None:
        width, height = self.canvas.current_dimensions
        padding = (ICON_SIZE / 2) + 10
        layout_size = padding + ICON_SIZE
        col_count = width // layout_size
        logging.info(
            "auto grid layout: dimension(%s, %s) col(%s)", width, height, col_count
        )
        for i, node in enumerate(self.canvas.nodes.values()):
            col = i % col_count
            row = i // col_count
            x = (col * layout_size) + padding
            y = (row * layout_size) + padding
            node.move(x, y)

    def click_edge_label_change(self) -> None:
        for edge in self.canvas.edges.values():
            edge.draw_labels()
