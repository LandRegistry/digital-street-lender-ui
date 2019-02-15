# Import every blueprint file
from lender_ui.views import general, index, lender_admin, login


def register_blueprints(app):
    """Adds all blueprint objects into the app."""
    app.register_blueprint(general.general)
    app.register_blueprint(index.index)
    app.register_blueprint(lender_admin.admin, url_prefix="/admin")
    app.register_blueprint(login.login)

    # All done!
    app.logger.info("Blueprints registered")
