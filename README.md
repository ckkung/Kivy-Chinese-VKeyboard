# Kivy Chinese Virtual Keyboard

## Backup vkeyboard.py
sudo mv /usr/local/lib/python2.7/dist-packages/kivy/uix/vkeyboard.py /usr/local/lib/python2.7/dist-packages/kivy/uix/vkeyboard-org.py

## Installation

cd ~/

git clone https://github.com/ckkung/Kivy-Chinese-VKeyboard.git

### 安裝 香港參考宋體 DFSonfSd.ttf 字體，以便系統完全支持二萬九千餘漢字

cd Kivy-Chinese-VKeyboard/kivy/data/

mkdir fonts

cd fonts

wget http://glyph.iso10646hk.net/download/DFSongSd.ttf

cd ~/Kivy-Chinese-VKeyboard

sudo cp -r kivy /usr/local/lib/python2.7/dist-packages/

### 有關 DFSonfSd.ttf 版權

http://glyph.iso10646hk.net/chinese/download_001.jsp

## Active chinese keyboard
nano ~/.kivy/config.ini 

	keyboard_mode = dock
	keyboard_layout = chinese

## English keyboard
![](./png/english_keyboard.png)

## Simplified (簡易五代) Chinese keyboard
![](./png/simplex5_keyboard.png)

## Changjei5 (倉頡五代) Chinese keyboard
![](./png/cj5_keyboard.png)

## How to use

Press ![](./png/chinese.png) to change Chinese keybaord

Press ![](./png/english.png) to change English keyboard

Press ![](./png/cj5.png) / ![](./png/simplex5.png) to change next input method

![](./png/simplex5.png) Simplified (簡易五代) input method

![](./png/cj5.png) Changjei5 (倉頡五代) input method

![](./png/key.png)
