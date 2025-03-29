# DriverManager

The DriverManager is a unified browser automation solution for the ChatMate system. It consolidates functionality from both the legacy DriverSessionManager and DriverManager implementations, providing a clean and consistent interface for browser automation.

## Features

- **Singleton Pattern**: Ensures only one driver instance exists across the application
- **Session Management**: Automatic session expiration and renewal
- **Persistent Profiles**: Support for persistent Chrome profiles or temporary profiles in headless mode
- **Cookie Management**: Save and load cookies for session persistence
- **Mobile Emulation**: Option to emulate mobile devices for testing responsive designs
- **Context Management**: Built-in support for the Python `with` statement
- **Retry Mechanisms**: Resilient browser operations with automatic retries
- **Flexible Driver Options**: Support for both regular Chrome and undetected Chrome

## Usage Examples

### Basic Usage

```python
from core.DriverManager import DriverManager

# Create a driver manager instance
manager = DriverManager(headless=False)

# Get the driver
driver = manager.get_driver()

# Use the driver
driver.get("https://example.com")

# Quit the driver when done
manager.quit_driver()
```

### Context Manager (Recommended)

```python
from core.DriverManager import DriverManager

# Use with statement for automatic cleanup
with DriverManager(headless=True) as manager:
    driver = manager.get_driver()
    driver.get("https://example.com")
    # Driver will be automatically quit when exiting the with block
```

### Session Management

```python
from core.DriverManager import DriverManager

manager = DriverManager(max_session_duration=1800)  # 30 minutes
driver = manager.get_driver()

# Check if session is expired
if manager._is_session_expired():
    manager.refresh_session()

# Get current session info
session_info = manager.get_session_info()
print(session_info)
```

### Cookie Management

```python
from core.DriverManager import DriverManager

with DriverManager(cookie_file="my_cookies.pkl") as manager:
    driver = manager.get_driver()
    driver.get("https://example.com")
    
    # After login
    manager.save_cookies()
    
    # Later, load the cookies
    manager.load_cookies()
```

### Resilient Operations

```python
from core.DriverManager import DriverManager
from selenium.webdriver.common.by import By

manager = DriverManager()
driver = manager.get_driver()

def click_element():
    element = driver.find_element(By.ID, "my-button")
    element.click()
    return True

# Execute with retry on failure
result = manager.execute_with_retry(click_element, max_retries=5)
```

## Configuration Options

The DriverManager accepts the following configuration options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `profile_dir` | str | "./chrome_profile/default" | Path to the Chrome profile directory |
| `driver_cache_dir` | str | "./drivers" | Path to store downloaded WebDrivers |
| `headless` | bool | False | Whether to run in headless mode |
| `cookie_file` | str | "./cookies/default.pkl" | Path to store browser cookies |
| `wait_timeout` | int | 10 | Default timeout for WebDriverWait |
| `mobile_emulation` | bool | False | Whether to emulate a mobile device |
| `additional_arguments` | List[str] | [] | Additional Chrome command-line options |
| `undetected_mode` | bool | True | Use undetected_chromedriver instead of regular selenium |
| `max_session_duration` | int | 3600 | Maximum session duration in seconds |
| `retry_attempts` | int | 3 | Number of retry attempts for driver operations |
| `retry_delay` | int | 5 | Delay between retry attempts in seconds |

## Backward Compatibility

The DriverManager maintains backward compatibility with the legacy DriverSessionManager through a compatibility wrapper in the `core/__init__.py` file. This allows existing code to continue working without modification.

## Troubleshooting

If you encounter issues with the DriverManager, check the following:

1. Ensure you have Chrome installed and up to date
2. Check the driver logs in the logs directory
3. Try clearing the Chrome profile directory if experiencing login issues
4. Ensure the ChromeDriver version is compatible with your Chrome version

For persistent issues, consider using the `execute_with_retry` method or increasing the `retry_attempts` configuration. 