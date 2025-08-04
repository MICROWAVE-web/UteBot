def scrollbarstyle(margins=False, theme="dark"):
    if theme == "light":
        background = "#f0f0f0"
        handle_color = "#cccccc"
        border_color = "#e0e0e0"
    else:  # dark theme
        background = "#1a1a4f"
        handle_color = "#28368a"
        border_color = "#2A2929"

    return f'''
/* ===================== QScrollBar ======================= */
QScrollBar:vertical {{
    background: {background};
    width: {19 if margins else 10}px;
    margin: 0px 0px 0px {8 if margins else 0}px;   
    border: 0px transparent {border_color};
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {handle_color};                    
    min-height: 5px;
    border-radius: 4px;
}}
QScrollBar::sub-line:vertical {{
    margin: 0px 0px 0px 0px;
    height: 0px;
    width: 10px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}}
QScrollBar::add-line:vertical {{
    margin: 0px 0px 0px 0px;
    height: 0px;
    width: 10px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}}

QScrollBar:horizontal {{
    background: {background};
    height: {18 if margins else 10}px;
    margin: {8 if margins else 0}px 0px 0px 0px;    
    border: 1px transparent {border_color};
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {handle_color};                    
    min-height: 5px;
    border-radius: 4px;
}}
QScrollBar::sub-line:horizontal {{
    margin: 0px 0px 0px 0px;
    height: 0px;
    width: 10px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}}
QScrollBar::add-line:horizontal {{
    margin: 0px 0px 0px 0px;
    height: 0px;
    width: 10px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}}

QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal {{
    background: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
'''

# Пример использования
if __name__ == "__main__":
    print(scrollbarstyle(margins=True, theme="light"))
