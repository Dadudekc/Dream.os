# sync_ops/micro_factories/sync_ops_factory.py

from sync_ops.services.sync_ops_service import SyncOpsService

class SyncOpsFactory:
    """
    A simple factory for creating and managing a singleton instance of SyncOpsService.
    """

    _instance = None

    @classmethod
    def get_service(cls, user_name="Victor", logger=None):
        """
        Returns a singleton instance of SyncOpsService.
        
        :param user_name: Optional override for the user's name.
        :param logger: Optional logger to pass to the service.
        :return: An instance of SyncOpsService.
        """
        if cls._instance is None:
            cls._instance = SyncOpsService(user_name=user_name, logger=logger)
        return cls._instance

    @classmethod
    def reset_service(cls):
        """
        Resets the service instance. Useful for testing or reinitialization.
        """
        cls._instance = None