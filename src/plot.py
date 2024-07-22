import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates

colors=["blue","green","red","black","purple","orange","brown"]

matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42

# ------------------------------------------------------- #
def plot_graph(points, logx=False, logy=False, xlabel="xlabel",\
            ylabel="ylabel", filename="noname.pdf", loc=2,\
               vlines=[], xnorm=1, xmin=0, xmax=None, vpos=0.5, ymax=1,
               legend=True, rotatex=None, isdate=False, xticks=[],
               xticks_label=[]):

    plt.figure(figsize=(8,6))

    siter = iter(["--",":","-.","-","--",":","-.","-"])
    for t, xs, ys, color, label in points:
        if(not isdate):
            xs = [x/float(xnorm) for x in xs]

        if(t == "step"):
            plt.step(xs, ys, color=color, linestyle=next(siter), linewidth=3,\
                     label=label, where="post")
        if(t == "line"):
            if(isdate):
                xs = matplotlib.dates.date2num(xs)
                plt.plot_date(xs, ys, color=color, linestyle=next(siter), linewidth=3,\
                     label=label)
            else:
                plt.plot(xs, ys, color=color, linestyle=next(siter), linewidth=3,\
                     label=label)
        if(t == "points"):
            plt.plot(xs, ys, color=color, linestyle="None", marker='o', markersize=12,\
                     label=label)
    if(vlines):
        for l,label in vlines:
            plt.axvline(x=l, color='black', linestyle="--", linewidth=2)
            plt.text(l*1.05, vpos, label, rotation=90)

    if(xticks_label):
        plt.xticks(fontsize=20, ticks=xticks, labels=xticks_label)
    else:
        plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)

    if(legend):
        plt.legend(fontsize=17, loc=loc, edgecolor="black")
    plt.gcf().subplots_adjust(bottom=0.21, left=0.20)

    plt.xlabel(xlabel, fontsize=20)
    plt.ylabel(ylabel, fontsize=20)

    if(rotatex):
        plt.xticks(rotation=45)

    if(xmin):
        plt.xlim(xmin=xmin,xmax=xmax)
    plt.ylim(ymin=0, ymax=ymax)

    if logx:
        plt.xscale('log')
    if logy:
        plt.yscale('log')

    plt.tight_layout()
    plt.savefig(filename,bbox_inches="tight")
    plt.close()
    plt.clf()

