Raspberry Virtual Keyboard with touch screen


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

![](./png/english_keyboard.png)

## Simplified (速成) Chinese keyboard
![](./png/simplex_keyboard.png)

## Simplified (簡易五代) Chinese keyboard
![](./png/simplex5_keyboard.png)

## Changjei5 (倉頡五代) Chinese keyboard
![](./png/cj5_keyboard.png)

## How to use

Press ![](./png/chinese.png) to change Chinese keybaord

Press ![](./png/english.png) to change English keyboard

Press ![](./png/cj5.png) / ![](./png/simplex5.png) / ![](./png/simplex.png) to change another input method

![](./png/cj5.png) Changjei5 (倉頡五代) input method

![](./png/simplex5.png) Simplified (簡易五代) input method

![](./png/simplex.png) Simplified (速成) input method

![](./png/key.png)
