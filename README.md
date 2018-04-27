This is my first Kivy project for Raspberry with touch screen.


## Backup vkeyboard.py
sudo mv /usr/local/lib/python2.7/dist-packages/kivy/uix/vkeyboard.py /usr/local/lib/python2.7/dist-packages/kivy/uix/vkeyboard-org.py

## Installation
cd ~/

git clone https://github.com/ckkung/Kivy-VKeyboard.git

cd Kivy-VKeyboard

sudo cp -r kivy /usr/local/lib/python2.7/dist-packages/

## Active chinese keyboard
nano ~/.kivy/config.ini 

	keyboard_mode = dock
	keyboard_layout = chinese

## English keyboard
![](./png/Chinese.png)

## Chinese keyboard
Simplified input method

![](./png/Simplified-1.png)
![](./png/Simplified-2.png)

Cangjie input method

![](./png/Cangjie-1.png)
![](./png/Cangjie-2.png)

## How to use

Press ![](./png/English_Chinese.png) to change English / Chinese keybaord

Press ![](./png/Chinese_input.png) to change Chinese input method

![](./png/Chinese_select.png)
