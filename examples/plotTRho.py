import mesaPlot as mp
import matplotlib.pyplot as plt


m=mp.MESA()
m.loadProfile(num=-1)
p=mp.plot()

fig=plt.figure(figsize=(12,10))
ax=fig.add_subplot(111)


#Simply plot
p.plotTRho(m,fig=fig,ax=ax,show=False,showAll=True)
plt.show()

