def scrollbarstyle(margins=False):
    return f'''
/* ===================== QScrollBar ======================= */
QScrollBar:vertical {{
    background: #1a1a4f;
    width: {19 if margins else 10}px;
    margin: 0px 0px 0px {8 if margins else 0}px;   
    border: 0px transparent #2A2929;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: #28368a;                    
    min-height: 5px;
    border-radius: 4px;
    /* border-image: url(icons/scroll.png) 0 0 0 0;      /* <---- установите свое изображение */ 
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
    background: #1a1a4f;
    height: {18 if margins else 10}px;
    margin: {8 if margins else 0}px 0px 0px 0px;    
    border: 1px transparent #2A2929;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: #28368a;                    
    min-height: 5px;
    border-radius: 4px;
    /* border-image: url(icons/scroll.png) 0 0 0 0;       <---- установите свое изображение */ 
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