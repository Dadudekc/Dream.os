import sys
import threading
from PyQt5.QtWidgets import QApplication, QMessageBox
from interfaces.pyqt.DreamscapeMainWindow import DreamscapeMainWindow
from interfaces.pyqt.dreamscape_services import DreamscapeService
from interfaces.pyqt.feedback_dashboard import FeedbackDashboard


class IntegratedMainWindow(DreamscapeMainWindow):
    def __init__(self):
        super().__init__()

        # Business logic service (handles backend operations)
        self.service = DreamscapeService()

        # Feedback dashboard (optional)
        self.dashboard = None

        # Wire up UI actions AFTER UI components are initialized
        self._wire_ui_actions()

    def _wire_ui_actions(self):
        """Connect UI buttons to business logic functions."""
        # ----- PROMPT ACTIONS -----
        try:
            self.execute_prompt_btn.clicked.disconnect()
        except Exception:
            pass
        self.execute_prompt_btn.clicked.connect(self.on_execute_prompt)

        try:
            self.save_prompt_btn.clicked.disconnect()
        except Exception:
            pass
        self.save_prompt_btn.clicked.connect(self.on_save_prompt)

        try:
            self.reset_prompts_btn.clicked.disconnect()
        except Exception:
            pass
        self.reset_prompts_btn.clicked.connect(self.on_reset_prompts)

        # ----- DISCORD BOT ACTIONS -----
        try:
            self.launch_bot_btn.clicked.disconnect()
        except Exception:
            pass
        self.launch_bot_btn.clicked.connect(self.on_launch_discord_bot)

        try:
            self.stop_bot_btn.clicked.disconnect()
        except Exception:
            pass
        self.stop_bot_btn.clicked.connect(self.on_stop_discord_bot)

        # ----- OPTIONAL: Launch dashboard button (if added to UI) -----
        # self.launch_dashboard_btn.clicked.connect(self.on_launch_dashboard)

    # -------------------------------------------------------------------------
    # PROMPT EXECUTION HANDLERS
    # -------------------------------------------------------------------------
    def on_execute_prompt(self):
        prompt_text = self.prompt_editor.toPlainText().strip()

        if not prompt_text:
            QMessageBox.warning(self, "Empty Prompt", "Please enter a prompt before executing.")
            return

        def task():
            try:
                self.append_output("🚀 Executing prompt...")
                responses = self.service.execute_prompt(prompt_text)
                for response in responses:
                    self.append_output(f"✅ Response:\n{response}\n")
            except Exception as e:
                self.append_output(f"❌ Error during prompt execution: {str(e)}")

        threading.Thread(target=task, daemon=True).start()

    def on_save_prompt(self):
        try:
            self.service.prompt_manager.save_prompts()
            self.append_output("💾 Prompts saved successfully.")
        except Exception as e:
            self.append_output(f"❌ Error saving prompts: {str(e)}")

    def on_reset_prompts(self):
        try:
            self.service.prompt_manager.reset_to_defaults()
            self.append_output("🔄 Prompts reset to defaults.")
        except Exception as e:
            self.append_output(f"❌ Error resetting prompts: {str(e)}")

    # -------------------------------------------------------------------------
    # DISCORD BOT HANDLERS
    # -------------------------------------------------------------------------
    def on_launch_discord_bot(self):
        bot_token = self.discord_token_input.text().strip()
        channel_id_text = self.discord_channel_input.text().strip()

        if not bot_token or not channel_id_text.isdigit():
            QMessageBox.warning(self, "Invalid Input", "Enter a valid Discord Bot Token and numeric Channel ID.")
            return

        channel_id = int(channel_id_text)

        try:
            self.service.launch_discord_bot(bot_token, channel_id, log_callback=self.append_discord_log)
            self.update_discord_status(connected=True)
            self.append_output("✅ Discord bot launched successfully.")
        except Exception as e:
            self.append_output(f"❌ Error launching Discord bot: {str(e)}")

    def on_stop_discord_bot(self):
        try:
            self.service.stop_discord_bot()
            self.update_discord_status(connected=False)
            self.append_output("🛑 Discord bot stopped successfully.")
        except Exception as e:
            self.append_output(f"❌ Error stopping Discord bot: {str(e)}")

    # -------------------------------------------------------------------------
    # FEEDBACK DASHBOARD (Optional)
    # -------------------------------------------------------------------------
    def on_launch_dashboard(self):
        if not self.dashboard:
            self.dashboard = FeedbackDashboard()
        self.dashboard.show()

    # -------------------------------------------------------------------------
    # LOGGING & UI HELPERS
    # -------------------------------------------------------------------------
    def append_output(self, text: str):
        """Send logs to console and, if available, to a UI text area."""
        print(text)
        if hasattr(self, "output_log_viewer"):
            self.output_log_viewer.append(text)

    def append_discord_log(self, text: str):
        """Send logs to the Discord Bot log viewer."""
        print(f"Discord Log: {text}")
        if hasattr(self, "discord_log_viewer"):
            self.discord_log_viewer.append(text)

    def update_discord_status(self, connected: bool):
        status = "🟢 Connected" if connected else "🔴 Disconnected"
        if hasattr(self, "discord_status_label"):
            self.discord_status_label.setText(f"Status: {status}")
        print(f"Discord Status Updated: {status}")


# -------------------------------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IntegratedMainWindow()
    window.show()
    sys.exit(app.exec_())
