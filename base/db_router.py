class RatesRouter:
    """
    Routes all models in the 'base' app to the 'rates' database.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'base':
            return 'rates'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'base':
            return 'rates'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label == 'base' or
            obj2._meta.app_label == 'base'
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'base':
            return db == 'rates'
        return None
