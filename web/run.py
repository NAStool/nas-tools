from web.main import create_app


def run_webhook():
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=3000,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    run_webhook()
