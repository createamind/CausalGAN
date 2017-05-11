import tensorflow as tf
import numpy as np
import os
import scipy.misc
import numpy as np
from tqdm import trange

import pandas as pd
from itertools import combinations, product
import sys


from utils import save_image#makes grid image plots


def take_product(do_dict):
    '''
    this function takes some dictionary like:
        {key1:1, key2:[a,b], key3:[c,d]}
    and returns the dictionary:
        {key1:[1,1,1], key2[a,a,b,b,],key3[c,d,c,d]}
    computing the product of values
    '''
    values=[]
    for v in do_dict.values():
        if hasattr(v,'__iter__'):
            values.append(v)
        else:
            values.append([v])#allows scalar to be passed

    prod_values=np.vstack(product(*values))
    return {k:np.array(v) for k,v in zip(do_dict.keys(),zip(*prod_values))}


def chunks(input_dict, chunk_size):
    """
    Yield successive n-sized chunks.
    Takes a dictionary of iterables and makes an
    iterable of dictionaries
    """
    n=chunk_size
    batches=[]

    L=len(input_dict.values()[0])
    for i in xrange(0, L, n):
        fd={}
        n=n- max(0, (i+n) - L )#incase doesn't evenly divide
        for key,value in input_dict.items():
            fd[key]=value[i:i+n]

        batches.append(fd)
    return batches


def do2feed( do_dict, model, on_logits=True):
    '''
    this contains logit for parsing "do_dict"
    into a feed dict that can actually be worked with
    '''
    feed_dict={}
    for key,value in do_dict.items():
        if isinstance(key,tf.Tensor):
            feed_dict[key]=value
        elif isinstance(key,str):
            if key in model.cc.node_names:
                node=model.cc.node_dict[key]
                if on_logits:# intervene on logits by default
                    feed_dict[node.label_logit]=value
                else:
                    feed_dict[node.label]=value
            elif hasattr(model,key):
                feed_dict[getattr(model,key)]=value
            else:
                raise ValueError('string keys must be attributes of either\
                                 model.cc or model. Got string:',key)
        else:
            raise ValueError('keys must be tensors or strings but got',type(key))

    #Make sure [64,] isn't passed to [64,1] for example
    for tensor,value in feed_dict.items():
        feed_dict[tensor]=np.reshape(value,tensor.get_shape().as_list())

    return feed_dict



def once_sample(model, fetch, do_dict=None, step=None):
    pass


def sample(model, fetch=None, do_dict=None, on_logits=True):
    '''
    fetch should be a list of tensors to do sess.run on
    do_dict is a list of strings or tensors of the form:
    {'Male':1, model.z_gen:[0,1], model.cc.Smiling:[0.1,0.9]}
    '''

    if fetch==None:
        #assume images
        fetch=model.G

    p_do_dict=take_product(do_dict)

    ##Need divisible batch_size for most models
    L=len(p_do_dict.values()[0])
    if not L % model.batch_size == 0:
        raise ValueError('do_dict must be dividable by batch_size\
                         but instead product of inputs was of length',L)
    feed_dict= do2feed(p_do_dict, model, on_logits=on_logits)

    fds=chunks(feed_dict,model.batch_size)

    outputs=[]
    for fd in fds:
        out=model.sess.run(fetch, fd)
        outputs.append(out)

    return np.vstack(outputs), feed_dict

def intervention2d(model, fetch=None, do_dict=None, on_logits=True, step=''):
    '''
    This function is a wrapper around the more general function "sample".
    In this function, the do_dict is assumed to have only two varying
    parameters on which a 2d interventions plot can be made.
    '''

    #Interpret defaults:
    n_defaults=len( filter(lambda l:l is 'model_default', do_dict.values() ))

    print(n_defaults,' default values given..using 8 for each of them')

    try:
        for key,value in do_dict.items():
            if value == 'model_default':
                itv_min,itv_max=model.intervention_range[key]
                do_dict[key]=np.linspace(itv_min,itv_max,8)
            else:
                #otherwise pass a number, list, or array
                assert(not isinstance(value,str))

    except Exception, e:
        raise(e,'Difficulty accessing default model interventions')


    str_step=str(step)

    lengths = [ len(v) for v in do_dict.values() if hasattr(v,'__len__') ]
    #print('lengths',lengths)
    print 'lengths',lengths

    gt_one = filter(lambda l:l>1,lengths)

    if not 1<=len(gt_one)<=2:
        raise ValueError('for visualizing intervention, must have 1 or 2 parameters varying')
    nrows=gt_one[0]


    #Terminology
    if model.model_name=='began':
        result_dir=model.model_dir
        if str_step=='':
            str_step=str( model.sess.run(model.step) )+'_'
    elif model.model_name=='dcgan':
        result_dir=model.checkpoint_dir


    sample_dir=os.path.join(result_dir,'sample_figures')
    if not os.path.exists(sample_dir):
        os.mkdir(sample_dir)

    images, feed_dict= sample(model,fetch=model.G, do_dict=do_dict,on_logits=on_logits)


    itv_file=os.path.join(sample_dir, str_step+'intervention2d.png')
    #if os.path.exists(itv_file):
    #    itv_file='new'+itv_file #don't overwrite

    print '[*] saving intervention2d:',itv_file
    save_image(images,itv_file,nrow=nrows)






