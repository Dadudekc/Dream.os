# views/file_browser_widget.py

import os
import shutil
from PyQt5 import QtWidgets, QtCore, QtGui
from interfaces.pyqt.GuiHelpers import GuiHelpers  # Adjust path if needed
from pathlib import Path
from typing import Optional

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
    """Enhanced file browser widget with advanced filtering and context menu."""
    
    file_selected = QtCore.pyqtSignal(str)  # Keep existing signal

    def __init__(self, parent=None, root_dir: Optional[str] = None):
        super().__init__(parent)
        self.root_dir = root_dir or os.getcwd()
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons")
        self.view_mode = "Emoji"  # Default view mode

        self.setup_ui()
        self.populate_tree(self.root_dir)

    def setup_ui(self):
        """Initialize the UI components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Search bar with match counter
        search_layout = QtWidgets.QHBoxLayout()
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholder("Search files (fuzzy match)")
        self.search_box.textChanged.connect(self.filter_tree)
        self.match_counter = QtWidgets.QLabel("0 matches")
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.match_counter)
        layout.addLayout(search_layout)
        
        # File tree
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Name"])
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.tree)
        
    def populate_tree(self, directory):
        self.tree.clear()
        root_item = self.create_tree_item(directory, is_folder=True)
        self.tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)
        self.add_placeholder(root_item)

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
            self.file_selected.emit(file_path)

    def open_context_menu(self, position):
        """Show context menu with enhanced file operations."""
        item = self.tree.itemAt(position)
        if item is None:
            return

        file_path = item.data(0, QtCore.Qt.UserRole)
        menu = QtWidgets.QMenu()

        # File operations
        menu.addAction("Open", lambda: self.file_selected.emit(file_path))
        menu.addAction("Open Externally", lambda: self.open_externally(file_path))
        menu.addSeparator()
        
        # Clipboard operations
        menu.addAction("Copy Path", lambda: self.copy_path_to_clipboard(file_path))
        menu.addAction("Reveal in Explorer", lambda: self.reveal_in_explorer(file_path))
        menu.addSeparator()
        
        # File management
        menu.addAction("Duplicate", lambda: self.duplicate_file_or_folder(file_path))
        menu.addAction("Rename", lambda: self.rename_item(item, file_path))
        menu.addAction("Delete", lambda: self.delete_item(item, file_path))
        menu.addSeparator()
        
        # Creation operations
        create_menu = menu.addMenu("New")
        create_menu.addAction("File", self.create_new_file)
        create_menu.addAction("Folder", self.create_new_folder)

        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def copy_path_to_clipboard(self, path: str):
        """Copy file path to clipboard."""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(str(Path(path)))
        self.show_status_message(f"📋 Copied path: {path}")

    def reveal_in_explorer(self, path: str):
        """Open containing folder in system file explorer."""
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(Path(path).parent))
        )

    def duplicate_file_or_folder(self, path: str):
        """Create a copy of the selected file or folder."""
        source_path = Path(path)
        base_path = source_path.parent / source_path.stem
        counter = 1
        
        while True:
            suffix = f"_copy{counter}" if counter > 1 else "_copy"
            new_path = base_path.with_name(f"{source_path.stem}{suffix}{source_path.suffix}")
            if not new_path.exists():
                break
            counter += 1

        try:
            if source_path.is_dir():
                shutil.copytree(str(source_path), str(new_path))
            else:
                shutil.copy2(str(source_path), str(new_path))
            self.populate_tree(self.root_dir)
            self.show_status_message(f"✅ Duplicated: {new_path.name}")
        except Exception as e:
            self.show_status_message(f"❌ Duplicate failed: {e}")

    def create_new_file(self):
        """Create a new file in the current directory."""
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "New File", "Enter file name:"
        )
        if ok and new_name:
            try:
                new_path = Path(self.root_dir) / new_name
                new_path.touch()
                self.populate_tree(self.root_dir)
                self.show_status_message(f"✅ Created file: {new_name}")
            except Exception as e:
                self.show_status_message(f"❌ Could not create file: {e}")

    def create_new_folder(self):
        """Create a new folder in the current directory."""
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "New Folder", "Enter folder name:"
        )
        if ok and new_name:
            try:
                new_path = Path(self.root_dir) / new_name
                new_path.mkdir(parents=True, exist_ok=True)
                self.populate_tree(self.root_dir)
                self.show_status_message(f"✅ Created folder: {new_name}")
            except Exception as e:
                self.show_status_message(f"❌ Could not create folder: {e}")

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

    def filter_tree(self, text: str):
        """Filter tree with fuzzy matching support."""
        text = text.lower()
        match_count = 0
        
        def filter_item(item) -> bool:
            nonlocal match_count
            match = False
            
            # Check children recursively
            for i in range(item.childCount()):
                child = item.child(i)
                child_match = filter_item(child)
                if child_match:
                    match = True
            
            # Check current item
            item_text = item.text(0).lower()
            tokens = text.split()
            if all(token in item_text for token in tokens):
                match = True
                match_count += 1
            
            item.setHidden(not match)
            return match
        
        # Apply filter
        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))
            
        # Update counter
        self.match_counter.setText(f"{match_count} matches")

    def show_status_message(self, message: str):
        """Show status message (implement based on your logging system)."""
        print(message)  # Replace with your preferred logging method
