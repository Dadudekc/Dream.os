# views/file_browser_widget.py

import os
import shutil
from PyQt5 import QtWidgets, QtCore, QtGui
from ..GUI.GuiHelpers import GuiHelpers  # Adjust path if needed

class FileTreeWidget(QtWidgets.QTreeWidget):
    """
    A QTreeWidget subclass that supports internal drag-and-drop,
    multi-selection, and folder dragging.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        paths = []
        for item in selected_items:
            path = item.data(0, QtCore.Qt.UserRole)
            if path:
                paths.append(path)
        
        if not paths:
            return

        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()
        mimeData.setText("\n".join(paths))
        drag.setMimeData(mimeData)
        
        first_item = selected_items[0]
        if first_item.icon(0) and not first_item.icon(0).isNull():
            drag.setPixmap(first_item.icon(0).pixmap(32, 32))
        
        drag.exec_(supportedActions)

class FileBrowserWidget(QtWidgets.QWidget):
    """
    IDE-style expandable file explorer with search, context menus, and a view mode toggle.
    Emits a custom signal 'fileDoubleClicked' when a file is double-clicked.
    """
    fileDoubleClicked = QtCore.pyqtSignal(str)

    def __init__(self, root_dir=None, helpers=None, parent=None):
        super().__init__(parent)
        self.helpers = helpers if helpers else GuiHelpers()
        self.root_dir = root_dir or os.getcwd()
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons")
        self.view_mode = "Emoji"  # Default view mode

        self.init_ui()
        self.populate_tree(self.root_dir)

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # View Mode Toggle
        self.view_mode_combo = QtWidgets.QComboBox()
        self.view_mode_combo.addItems(["Emoji", "SVG", "Hybrid"])
        self.view_mode_combo.currentTextChanged.connect(self.switch_view_mode)
        layout.addWidget(self.view_mode_combo)

        # Search Bar
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search...")
        self.search_bar.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search_bar)

        # Current Directory Label
        self.path_label = QtWidgets.QLabel(f"Root: {self.root_dir}")
        layout.addWidget(self.path_label)

        # File Tree
        self.tree = FileTreeWidget()
        self.tree.setHeaderLabels(["File/Folder", "Type"])
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.viewport().setAcceptDrops(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)

        # Optional Preview Area (if desired; you can remove this if the main window handles preview)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)

    def switch_view_mode(self, mode):
        self.view_mode = mode
        self.populate_tree(self.root_dir)

    def populate_tree(self, directory):
        self.tree.clear()
        root_item = self.create_tree_item(directory, is_folder=True)
        self.tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)
        self.add_placeholder(root_item)
        self.path_label.setText(f"Root: {directory}")

    def create_tree_item(self, path, is_folder=False):
        base_name = os.path.basename(path)
        if is_folder:
            if self.view_mode == "Emoji":
                label = f"📂 {base_name}"
                type_label = "Folder"
                icon = QtGui.QIcon()  # No icon in Emoji mode
            elif self.view_mode == "SVG":
                label = base_name
                type_label = "Folder"
                icon = QtGui.QIcon(os.path.join(self.icon_path, "folder.svg"))
            else:  # Hybrid
                label = f"📂 {base_name}"
                type_label = "Folder"
                icon = QtGui.QIcon(os.path.join(self.icon_path, "folder.svg"))
        else:
            emoji, type_label = self.get_file_icon_and_type(path)
            if self.view_mode == "Emoji":
                label = f"{emoji} {base_name}"
                icon = QtGui.QIcon()
            elif self.view_mode == "SVG":
                label = base_name
                icon = QtGui.QIcon(self.get_svg_icon_path(path))
            else:
                label = f"{emoji} {base_name}"
                icon = QtGui.QIcon(self.get_svg_icon_path(path))
        item = QtWidgets.QTreeWidgetItem([label, type_label])
        item.setData(0, QtCore.Qt.UserRole, path)
        item.setIcon(0, icon)
        return item

    def get_svg_icon_path(self, path):
        _, ext = os.path.splitext(path.lower())
        mapping = {
            '.py': "python.svg",
            '.txt': "text.svg",
            '.json': "json.svg",
            '.csv': "csv.svg",
            '.md': "markdown.svg",
            '.html': "html.svg",
            '.css': "css.svg",
            '.js': "js.svg",
            '.exe': "exe.svg",
            '.zip': "zip.svg",
            '.jpg': "image.svg",
            '.jpeg': "image.svg",
            '.png': "image.svg",
            '.pdf': "pdf.svg"
        }
        return os.path.join(self.icon_path, mapping.get(ext, "file.svg"))

    def get_file_icon_and_type(self, path):
        _, ext = os.path.splitext(path.lower())
        mapping = {
            '.py':   ('🐍', 'Python Script'),
            '.txt':  ('📄', 'Text File'),
            '.json': ('🗂️', 'JSON File'),
            '.csv':  ('📑', 'CSV File'),
            '.md':   ('📝', 'Markdown File'),
            '.html': ('🌐', 'HTML File'),
            '.css':  ('🎨', 'CSS File'),
            '.js':   ('📜', 'JavaScript File'),
            '.exe':  ('⚙️', 'Executable'),
            '.zip':  ('🗜️', 'ZIP Archive'),
            '.jpg':  ('🖼️', 'JPEG Image'),
            '.jpeg': ('🖼️', 'JPEG Image'),
            '.png':  ('🖼️', 'PNG Image'),
            '.pdf':  ('📕', 'PDF Document')
        }
        return mapping.get(ext, ('📄', 'File'))

    def add_placeholder(self, item):
        placeholder = QtWidgets.QTreeWidgetItem(["Loading...", ""])
        item.addChild(placeholder)

    def on_item_expanded(self, item):
        path = item.data(0, QtCore.Qt.UserRole)
        if not os.path.isdir(path):
            return
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            item.takeChildren()
            self.add_children(item, path)

    def add_children(self, parent_item, path):
        try:
            for entry in sorted(os.listdir(path)):
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    child = self.create_tree_item(full_path, is_folder=True)
                    self.add_placeholder(child)
                else:
                    child = self.create_tree_item(full_path)
                parent_item.addChild(child)
        except Exception as e:
            self.helpers.log_to_output(None, f"❌ Error reading directory {path}: {e}")

    def on_item_double_clicked(self, item, column):
        file_path = item.data(0, QtCore.Qt.UserRole)
        if os.path.isdir(file_path):
            if not item.isExpanded():
                item.setExpanded(True)
        elif os.path.isfile(file_path):
            # Emit custom signal to notify main window.
            self.fileDoubleClicked.emit(file_path)

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None:
            return

        file_path = item.data(0, QtCore.Qt.UserRole)
        menu = QtWidgets.QMenu()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        properties_action = menu.addAction("Properties")
        open_ext_action = menu.addAction("Open Externally")
        switch_view_action = menu.addAction("Switch View Mode")

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))
        if action == rename_action:
            self.rename_item(item, file_path)
        elif action == delete_action:
            self.delete_item(item, file_path)
        elif action == properties_action:
            self.show_properties(file_path)
        elif action == open_ext_action:
            self.open_externally(file_path)
        elif action == switch_view_action:
            new_mode = {"Emoji": "SVG", "SVG": "Hybrid", "Hybrid": "Emoji"}[self.view_mode]
            self.view_mode = new_mode
            self.view_mode_combo.setCurrentText(new_mode)
            self.populate_tree(self.root_dir)

    def rename_item(self, item, file_path):
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename", "Enter new name:")
        if ok and new_name:
            dir_path = os.path.dirname(file_path)
            new_path = os.path.join(dir_path, new_name)
            try:
                os.rename(file_path, new_path)
                item.setText(0, new_name)
                item.setData(0, QtCore.Qt.UserRole, new_path)
                self.helpers.log_to_output(None, f"✅ Renamed to {new_name}")
            except Exception as e:
                self.helpers.log_to_output(None, f"❌ Rename failed: {e}")

    def delete_item(self, item, file_path):
        reply = QtWidgets.QMessageBox.question(self, "Delete", f"Delete {file_path}?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                parent = item.parent() or self.tree.invisibleRootItem()
                parent.removeChild(item)
                self.helpers.log_to_output(None, f"✅ Deleted {file_path}")
            except Exception as e:
                self.helpers.log_to_output(None, f"❌ Delete failed: {e}")

    def show_properties(self, file_path):
        info = os.stat(file_path)
        props = (f"Path: {file_path}\n"
                 f"Size: {info.st_size} bytes\n"
                 f"Modified: {QtCore.QDateTime.fromSecsSinceEpoch(info.st_mtime).toString()}")
        QtWidgets.QMessageBox.information(self, "Properties", props)

    def open_externally(self, file_path):
        try:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(file_path))
        except Exception as e:
            self.helpers.log_to_output(None, f"❌ Failed to open externally: {e}")

    # --- Filtering Methods ---
    def filter_tree(self, text):
        """Filter the tree items based on the search text."""
        text = text.lower()
        root = self.tree.invisibleRootItem()
        self.filter_tree_item(root, text)

    def filter_tree_item(self, item, text):
        """Recursively show/hide tree items based on whether they match the search text."""
        match = False
        for i in range(item.childCount()):
            child = item.child(i)
            child_visible = self.filter_tree_item(child, text)
            child.setHidden(not child_visible)
            if child_visible:
                match = True

        current_text = item.text(0).lower()
        if text in current_text:
            match = True

        return match
