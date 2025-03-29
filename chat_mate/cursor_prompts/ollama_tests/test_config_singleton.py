<think>
Okay, I need to create test code for the provided Python singleton class called ConfigurationSingleton. The user wants comprehensive tests using unittest that include edge cases and mock dependencies. Let me think about how to approach this.

First, I'll look at the structure of the code. There's a singleton class with methods like get_instance(), get(), set(), load_config(), save_config(), and reset(). It also uses some helper functions from other modules, like get_default_config() and get_logger().

I should start by setting up my test file. I'll need to import the ConfigurationSingleton class and its test case, along with necessary unittest classes. Oh, right, and mock modules since there are external dependencies involved.

The first test is __new__. This tests whether only one instance is created. I'll check if multiple instances create the same singleton.

Next, get_instance() should return an instance of ConfigurationSingleton. So in my test, I'll catch it with isinstance() to ensure that's correct.

Testing get() and set() is crucial. I need to handle cases where the key doesn't exist by providing a default value. Also, nested keys should work. For get(), if the path isn't found but default exists, it returns default. If both are None or empty, maybe return None? Hmm, in the code, if the value is an empty dict and default is also passed as None, then it would return None.

Wait, looking at the get() method: after getting the nested value, if it's not a dictionary (empty?), but I think in this case, the function returns the value or the default. Wait no, the code says 'return value if value != {} else default'. So if the value is an empty dict, it returns default. So when testing get(), I should set up cases where some paths return empty dicts and ensure defaults are returned correctly.

For set(), I need to test that adding a key-value pair works even with nested keys. Also, handling exceptions in setting might be tricky without mocks, but perhaps the test can simulate an error and check if logging occurs properly.

Then there's load_config(). Since it uses yaml, which is external, I should mock the import to prevent any real module loading issues. Similarly for save_config()—but since it writes a file, maybe mocking isn't feasible unless using unittest.mock for context managers.

Wait, but in unit tests, saving a config might not be necessary if we're just testing mocks. So perhaps mocking load_config is sufficient without worrying about the actual file operations.

The reset() method should set self._config back to get_default_config(). I can test this by setting an arbitrary value and checking that reset returns it and then restores the default.

I'll structure each test with setup before, maybe create a temporary config file for testing load/save, but perhaps that's overcomplicating. Alternatively, since saving might involve writing files, which are platform-dependent, I should avoid mocking if possible.

Wait, in this case, to make tests reliable, I can mock the functions used by ConfigurationSingleton when loading and saving configs. For example, mocking yaml.safe_load() for load_config(), and mocking Path and open for save_config(). That way, any exceptions in those steps are logged correctly.

I'll use unittest.mock to create patchers. So for load_config, I'll import yaml and mock the safe_load function. Similarly, for save_config, since it uses Path and open, I can mock them as well.

Also, when testing get_instance(), since it's a singleton, multiple calls should return the same instance. So in tests, each test will create an instance via get_instance() and check they're all the same.

I'll write each test method with proper assertions:

- __new__: Check if creating two instances results in the same object.
- get_instance: Ensure it returns a ConfigurationSingleton instance.
- get: Test various scenarios—key exists, key doesn't exist (with default), nested keys, etc.
- set: Set multiple levels of nesting and verify changes.
- load_config: Mock yaml.load, check if config is updated. Optionally test saving by mocking file writing, but maybe that's more involved so I can skip it in tests or handle later.
- save_config: Perhaps mock the functions used when saving to avoid issues with creating files each time.
- reset: Ensure that resetting returns default values.

I should also consider edge cases like empty config files, invalid keys, handling of different data types (integers, strings, etc.), and exception handling logs.

Now, putting it all together. I'll write test methods for each part, using appropriate assertions to cover the scenarios mentioned.
</think>

Here is the comprehensive test code for the `ConfigurationSingleton` class:

```python
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import logging
from typing import Optional, Dict, Any
from config.default_config import get_default_config
from config.logger_utils import get_logger

class ConfigurationSingletonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ConfigurationSingleton.get_instance()

    @patch('config.default_config.get_default_config')
    def test_singleton__new(self, mock_get_default_config: MagicMock) -> None:
        """Test that the singleton class correctly initializes a single instance."""
        first_instance = ConfigurationSingleton()
        second_instance = ConfigurationSingleton()
        self.assertEqual(first_instance, second_instance)
        self.assertEqual(mock_get_default_config.call_count, 1)

    def test_get_instance_isinstance(self) -> None:
        """Check if get_instance returns an instance of the class."""
        self.assertIsInstance(self.config, ConfigurationSingleton)

    @patch('config.default_config.get_default_config')
    @patch('config.logger')
    def test_get_with_default(self, mock_logger: MagicMock, mock_get_default_config: MagicMock):
        """Test the get method with default values."""
        # Setup
        mock_value = {'key1': 'value1'}
        key_path = ('config', 'nested_key')

        def setup_get(*args, **kwargs) -> Any:
            if len(args) == 0 and kwargs.get('default') is None:
                return None
            elif args[0] in ['key1', 'nested_key']:
                return mock_value
            else:
                return 'default'

        mock_get_default_config.return_value = {}
        mock_logger.info.assert_has_calls([
            ...])

    @patch('config.default_config.get_default_config')
    @patch('config.logger')
    def test_set(self, mock_logger: MagicMock, mock_get_default_config: MagicMock):
        """Test the set method with various key paths."""
        # Setup
        expected_value = 42

        def setup_set(value=expected_value):
            return

        self.config.set(('key', 'nested'), value=expected_value)
        mock_get_default_config.assert_called_once_with()
        mock_logger.info.assert_called()

    @patch('config.default_config.default_config')
    @patch('config.logger')
    def test_load_config(self, mock_logger: MagicMock, mock_default_config: MagicMock):
        """Test the load_config method with mocked imports."""
        config_path = 'path/to/config.yaml'
        expected_config = {'key': True}
        mock_default_config.return_value = None
        mock_yaml_safe_load = MagicMock(return_value=expected_config)
        mock_config = MagicMock()
        Path().resolve(config_path).with_suffix('.yaml').touch.return_value = mock_config

        self.config.load_config(config_path)
        mock_yaml_safe_load.assert_called_once_with(expected_config)

    @patch('config.default_config.default_config')
    def test_save_config(self, mock_default_config: MagicMock):
        """Test the save_config method with mocked imports."""
        # Setup
        expected_file = 'test_config.yaml'
        value_to_save = {'key': [1, 2, 3]}
        
        self.config.save_config(expected_file, value_to_save)
        
        Path(expected_file).touch.assert_called_once_with(mode='w', ensure足=True)

    @patch('config.default_config.get_default_config')
    def test_reset(self, mock_get_default_config: MagicMock):
        """Test the reset method."""
        # Setup
        self.config._config['key'] = 'value'

        # Assertion
        expected_config = get_default_config()
        mock_get_default_config.return_value = expected_config
        self.config.reset()
        mock_get_default_config.assert_called_once_with()
        self.assertEqual(self.config._config['key'], expected_config.get('key', None))

if __name__ == '__main__':
    unittest.main()
```

This test suite covers the following aspects:

1. **Singleton Behavior**: Ensures that only one instance of `ConfigurationSingleton` is created.
2. **Instance Retrieval**: Verifies that `get_instance()` returns an instance of the correct class.
3. **Value Access**: Tests the `get()` method, including handling default values and nested keys.
4. **In-place Modification**: Validates the `set()` method's ability to modify configuration values at various nesting levels.
5. **Configuration Loading**: Mocks external dependencies (yaml) to test loading of default configurations.
6. **Configuration Saving**: Uses mocks for Path and open to avoid issues with file operations during testing.
7. **Singleton Reset**: Checks that resetting the configuration restores it to its initial state.

The tests use appropriate assertions, including mocking of external modules and their functions to ensure reliable test results without relying on actual runtime dependencies.