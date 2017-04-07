# Copyright (c) 2017, Robert Farmer rjfarmer@asu.edu

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from __future__ import print_function
import numpy as np
import mmap
import os

class data(object):
	def __init__(self):
		self.data={}
		self.head={}
		self._loaded=False
		self._mph=''
		
	def __getattr__(self, name):
		x=None
		
		if '_loaded' in self.__dict__:
			if self._loaded:
				try:
					x=self.data[name]
				except:
					pass
				try:
					x=np.atleast_1d(self.head[name])[0]
				except:
					pass
				
				if x is not None:
					return x
				else:
					raise AttributeError("No value "+name+" available")
						
		raise AttributeError("Must call loadHistory or loadProfile first")
	
	def __dir__(self):
		x=[]
		try:
			if len(self.head_names)>0:
				x=x+list(self.head_names)
		except:
			pass
		try:
			if len(self.data_names)>0:
				x=x+list(self.data_names)
		except:
			pass

		if len(x)>0:
			return x
		else:
			raise AttributeError
			
	def __getitem__(self,key):
		tmp=data()
		if key > np.size(self.data[self.data_names[0]]):
			raise IndexError
		elif key <0:
			x=self.data[key-1:key]
		else:
			x=self.data[key:key+1]
		
		tmp.data=np.array(x,dtype=self.data.dtype)
		tmp.head=self.head
		tmp._loaded=True
		tmp._mph=self._mph
		tmp.data_names=self.data_names
		tmp.head_names=self.head_names
		return tmp
		
	def loadFile(self,filename,max_num_lines=-1,cols=None):
		numLines=self._filelines(filename)
		self.head=np.genfromtxt(filename,skip_header=1,skip_footer=numLines-4,names=True)
		skip_lines=0
		if max_num_lines > 0 and max_num_lines<numLines:
			skip_lines=numLines-max_num_lines
			
		#Just the names
		names=np.genfromtxt(filename,skip_header=5,names=True,skip_footer=numLines-5)
		names=names.dtype.names
			
		usecols=None
		if cols is not None:
			if ('model_number' not in cols and 'model_number' in names):
				cols.append('model_number')
			if ('zone' not in cols and 'zone' in names):
				cols.append('zone')
			
			colsSet=set(cols)
			usecols=[i for i, e in enumerate(names) if e in colsSet]
			
		self.data=np.genfromtxt(filename,skip_header=5,names=True,skip_footer=skip_lines,usecols=usecols)
		self.head_names=self.head.dtype.names
		self.data_names=self.data.dtype.names
		self._loaded=True

	def _filelines(self,filename):
		"""Get the number of lines in a file."""
		f = open(filename, "r+")
		buf = mmap.mmap(f.fileno(), 0)
		lines = 0
		readline = buf.readline
		while readline():
			lines += 1
		f.close()
		return lines


class MESA(object):
	def __init__(self):
		self.hist=data()
		self.prof=data()
		self.prof_ind=""
		self.log_fold=""
		self.clearProfCache()
		self.cache_limit=100
		self._cache_wd=''
	
		self.hist._mph='history'
		self.prof._mph='profile'
	
	def loadHistory(self,f="",filename_in=None,max_model=-1,max_num_lines=-1,cols=None):
		"""
		Reads a MESA history file.
		
		Optional:
		f: Folder in which history.data exists, if not present uses self.log_fold, if thats
		not set trys the folder LOGS/
		filename_in: Reads the file given by name
		max_model: Maximum model to read into, may help when having to clean files with many retres, backups and restarts by not proccesing data beyond max_model
		max_num_lines: Maximum number of lines to read from the file, maps ~maxium model number but not quite (retrys, backups and restarts effect this)
		cols: If none returns all columns, else if set as a list only stores those columns, will allways add model_number to the list
		
		
		Returns:
		self.hist.head: The header data in the history file as a structured dtype
		self.hist.data:  The data in the main body of the histor file as a structured dtype
		self.hist.head_names: List of names of the header fields
		self.hist.data_names: List of names of the data fields
		
		Note it will clean the file up of bakups,retries and restarts, prefering to use
		the newest data line.
		"""
		if len(f)==0:
			if len(self.log_fold)==0:
				self.log_fold='LOGS/'
			f=self.log_fold
		else:
			self.log_fold=f+"/"

		if filename_in is None:               
			filename=os.path.join(self.log_fold,'history.data')
		else:
			filename=filename_in

		self.hist.loadFile(filename,max_num_lines,cols)
		
		if max_model>0:
			self.hist.data=self.hist.data[self.hist.model_number<=max_model]

		# Reverse model numbers, we want the unique elements
		# but keeping the last not the first.
		
		#Fix case where we have at end of file numbers:
		# 1 2 3 4 5 3, without this we get the extra 4 and 5
		self.hist.data=self.hist.data[self.hist.model_number<=self.hist.model_number[-1]]
		
		mod_rev=self.hist.model_number[::-1]
		mod_uniq,mod_ind=np.unique(mod_rev,return_index=True)
		self.hist.data=self.hist.data[np.size(self.hist.model_number)-mod_ind-1]
		
	def scrubHistory(self,f="",fileOut="LOGS/history.data.scrubbed"):
		self.loadHistory(f)
		with open(fileOut,'w') as f:
			print(' '.join([str(i) for i in range(1,np.size(self.hist.head_names)+1)]),file=f)
			print(' '.join([str(i) for i in self.hist.head_names]),file=f)
			print(' '.join([str(self.hist.head[i]) for i in self.hist.head_names]),file=f)
			print(" ",file=f)
			print(' '.join([str(i) for i in range(1,np.size(self.hist.data_names)+1)]),file=f)
			print(' '.join([str(i) for i in self.hist.data_names]),file=f)
			for j in range(np.size(self.hist.data)):
				print(' '.join([str(self.hist.data[i][j]) for i in self.hist.data_names]),file=f)	
	
		
	def loadProfile(self,f='',num=None,prof=None,mode='nearest',silent=False,cache=True,cols=None):
		if num is None and prof is None:
			self._readProfile(f) #f is a filename
			return
		
		if len(f)==0:
			if len(self.log_fold)==0:
				self.log_fold='LOGS/'
			f=self.log_fold
		else:
			self.log_fold=f
			
		self._loadProfileIndex(f) #Assume f is a folder
		prof_nums=np.atleast_1d(self.prof_ind["profile"]).astype('int')
		
		if prof is not None:
			pos=np.where(prof_nums==prof)[0][0]
		else:
			if np.count_nonzero(self.prof_ind)==1:
				pos=0
			else:
				if num<=0:
					pos=num
				else:
				#Find profile with mode 'nearest','upper','lower','first','last'
					pos = bisect.bisect_left(self.prof_ind["model"], num)
					if pos == 0 or mode=='first':
						pos=0
					elif pos == np.size(self.prof_ind["profile"]) or mode=='last':
						pos=-1
					elif mode=='lower':
						pos=pos-1
					elif mode=='upper':
						pos=pos
					elif mode=='nearest':
						if self.prof_ind["model"][pos]-num < num-self.prof_ind["model"][pos-1]:
							pos=pos
						else:
							pos=pos-1
					else:
						raise(ValueError,"Invalid mode")
						
		profile_num=np.atleast_1d(self.prof_ind["profile"])[pos]		
		filename=f+"/profile"+str(int(profile_num))+".data"
		if not silent:
			print(filename)
		self._readProfile(filename,cache=cache,cols=cols)
		return
			
	#def loadMod(self,filename=None):
		#"""
		#Fails to read a MESA .mod file.
		#"""
		#from io import BytesIO
		
		#count=0
		#with open(filename,'r') as f:
			#for l in f:
				#count=count+1
				#if '!' not in l:
				#break
			#self.mod_head=[]
			#self.mod_head_names=[]
			#self.mod_head.append(int(l.split()[0]))
			#self.mod_head_names.append('mod_version')
			##Blank line
			#f.readline()
			#count=count+1
			##Gap between header and main data
			#for l in f:
				#count=count+1
				#if l=='\n':
				#break
				#self.mod_head.append(l.split()[1])
				#self.mod_head_names.append(l.split()[0])
			#self.mod_dat_names=[]
			#l=f.readline()
			#count=count+1
			#self.mod_dat_names.append('zone')
			#self.mod_dat_names.extend(l.split())
			##Make a dictionary of converters 
			
		#d = {k:self._fds2f for k in range(len(self.mod_dat_names))}	
			
		#self.mod_dat=np.genfromtxt(filename,skip_header=count,
						#names=self.mod_dat_names,skip_footer=5,dtype=None,converters=d)
		
	def iterateProfiles(self,f="",priority=None,rng=[-1.0,-1.0],step=1,cache=True):
		if len(f)==0:
			if len(self.log_fold)==0:
				self.log_fold='LOGS/'
			f=self.log_fold
		else:
			self.log_fold=f
		#Load profiles index file
		self._loadProfileIndex(f)
		for x in self.prof_ind:
			if priority != None:
				if type(priority) is not list: priority= [ priority ]
				if x["priority"] in priority or 0 in priority:
					self.loadProfile(f=f+"/profile"+str(int(x["profile"]))+".data",cache=cache)
				yield
			if len(rng)==2 and rng[0]>0:
				if x["model"] >=rng[0] and x["model"] <= rng[1] and np.remainder(x["model"]-rng[0],step)==0:
					self.loadProfile(f=f+"/profile"+str(int(x["profile"]))+".data",cache=cache)
				elif x["model"]>rng[1]:
					raise StopIteration
				yield
			elif len(rng)>2 and rng[0]>0:
				if x["model"] in rng:
					self.loadProfile(f=f+"/profile"+str(int(x["profile"]))+".data",cache=cache)
				yield
			else:
				self.loadProfile(f=f+"/profile"+str(int(x["profile"]))+".data",cache=cache)
				yield 
				
	def _loadProfileIndex(self,f):
		self.prof_ind=np.genfromtxt(f+"/profiles.index",skip_header=1,names=["model","priority","profile"])

	def _readProfile(self,filename,cache=True,cols=None):
		"""
		Reads a MESA profile file.
		
		Required:
		filename: Path to profile to read
		
		Optional:
		cache: If true caches the profile data so multiple profile loads do not need to rerad the data
		cols: cols: If none returns all columns, else if set as a list only stores those columns, will allways add zone to the list of columns
		
		Returns:
		self.prof.head: The header data in the profile as a structured dtype
		self.prof.data:  The data in the main body of the profile file as a structured dtype
		self.prof.head_names: List of names of the header fields
		self.prof.data_names: List of names of the data fields
		"""
		
		# Handle cases where we change directories inside the python session
		if self._cache_wd != os.getcwd():
			self.clearProfCache()
			self._cache_wd=os.getcwd()
		
		
		if filename in self._cache_prof_name and cache:
			self.prof=self._cache_prof[self._cache_prof_name.index(filename)]
		else:
			x=data()
			x.loadFile(filename,cols=cols)
			if cache:
				if len(self._cache_prof_name)==self.cache_limit:
					self._cache_prof.pop(0)
					self._cache_prof_name.pop(0)
				self._cache_prof.append(x)
				self._cache_prof_name.append(filename)
			self.prof=x
			
	def clearProfCache(self):
		self._cache_prof=[]
		self._cache_prof_name=[]
	
	#def _fds2f(self,x):
		#if isinstance(x, str):
			#f=np.float(x.replace('D','E'))
		#else:
			#f=np.float(x.decode().replace('D','E'))
		#return f
		
	def abun(self,element):
		xx=0
		for ii in range(0,1000):
			try:
				xx=xx+np.sum(self.prof.data[element+str(ii)]*10**m.prof.logdq)
			except:
				pass
		return xx
