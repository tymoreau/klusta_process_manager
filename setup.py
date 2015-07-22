import os
from setuptools import setup, find_packages
from config import create_user_config_file

def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

create_user_config_file(override=False)

setup(
	name="klusta_process_manager",
	version="0.5.0",
	url="https://github.com/tymoreau/klusta_process_manager",
	author="T.Moreau (INMED)",
	license='BSD',
	
	description="GUI to browse and process data in neuroscience, using klusta",
	long_description=read("README.md"),

	classifiers=[
		'Development Status :: 4 - Beta',

		'License :: OSI Approved :: BSD Licence',

		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3.4',
	],

	keywords="klusta neuroscience",

	packages=find_packages(exclude=['other','test'])+["klusta_process_manager.scripts"],
	
	package_data={
		'klusta_process_manager': ['icons/*.png'],
	},

	entry_points={
		'gui_scripts':[
			'klusta_process_manager = klusta_process_manager.scripts.runLocal:main',
			'klusta_server = klusta_process_manager.scripts.runServer:main',
		]
	}
	)


