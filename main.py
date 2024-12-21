from nicegui import ui

ui.colors(primary='#6E93D6', secondary='#53B689', accent='#111B1E', positive='#53B689')
def menu():
    with ui.row().classes('h-8 bg-black w-full pt-0 mt-0'):
        with ui.link('Home', '/').classes(replace='text-white'):
            ui.html(" ")
        ui.link('A', '/a').classes(replace='text-white')
        ui.link('B', '/b').classes(replace='text-white')
        ui.link('C', '/c').classes(replace='text-white')

@ui.page('/')
def index_page() -> None:
    menu()
    ui.label("Hellow World!!!")

ui.run(title='Modularization Example',reload=True)