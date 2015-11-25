def create_desktop_file_KDE():
	path="/usr/share/applications/klusta_process_manager.desktop"
	text=["[Desktop Entry]",
		  "Version=0.1",
		  "Name=klusta_process_manager",
		  "Comment=GUI",
		  "Exec=klusta_process_manager",
		  "Icon=eyes",
		  "Terminal=False",
		  "Type=Application",
		  "Categories=Applications;"]
	with open(path,"w") as f:
		f.write("\n".join(text))

if __name__=="__main__":
	print("Create a .desktop file in /usr/share/application")
	print("Only tested with Linux OpenSuse KDE")
	print("--------------")
	try:
		create_desktop_file_KDE()
		print("Shortcut created !")
	except PermissionError:
		print("Needs admin rights: try 'sudo python create_shortcut.py'")
