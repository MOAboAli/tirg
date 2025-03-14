# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Evaluates the retrieval model."""
import numpy as np
import pickle
import torch
from tqdm import tqdm as tqdm
from scipy.spatial import distance
import datasets
from BK import main2
import torchvision
from numpy.core.fromnumeric import argsort, squeeze
from tensorflow.python.ops.array_ops import zeros
from tensorflow.python.ops.gen_array_ops import concat
import torch
from torch import tensor
from torch.functional import norm
# from torch._C import float32
import torchvision
import torchvision.transforms as tvt
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np
from torch import optim
import torch.nn.functional as F
import math as m
import time
import os
import random
from PIL import Image
from torch.autograd import Variable
from PIL import Image
import numpy
import tensorflow as tf
from pathlib import Path
import pickle
import numpy as np
import torch
import torchvision
import torch.nn.functional as F
import text_model
import test_retrieval
import torch_functions
from tqdm import tqdm as tqdm
import PIL
import argparse
import datasets
import img_text_composition_models
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression
from sklearn.metrics import mean_squared_error


Path1=r"D:\personal\master\MyCode\files"
#Path1=r"C:\MMaster\Files"




################# Test by accessing image directly #########################

def test(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in tqdm(test_queries):
      imgs += [testset.get_img(t['source_img_id'])]
      mods += [t['mod']['str']]
      if len(imgs) >= opt.batch_size or t is test_queries[-1]:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)#.cuda()
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        all_queries += [f]
        imgs = []
        mods = []
    all_queries = np.concatenate(all_queries)
    all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)#.cuda()
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    for i in range(10000):
      print('get images=',i,end='\r')
      item = testset[i]
      imgs += [item['source_img_data']]
      mods += [item['mod']['str']]
      if len(imgs) >= opt.batch_size or i == 9999:
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy() #.cuda()
        all_queries += [f]
        imgs = []
        mods = []
      imgs0 += [item['target_img_data']]
      if len(imgs0) >= opt.batch_size or i == 9999:
        imgs0 = torch.stack(imgs0).float()
        imgs0 = torch.autograd.Variable(imgs0)
        imgs0 = model.extract_img_feature(imgs0).data.cpu().numpy() #.cuda()
        all_imgs += [imgs0]
        imgs0 = []
      all_captions += [item['target_caption']]
      all_target_captions += [item['target_caption']]
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testWbeta(opt, model, testset,beta):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()
 

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in tqdm(test_queries):
      imgs += [testset.get_img(t['source_img_id'])]
      mods += [t['mod']['str']]
      if len(imgs) >= opt.batch_size or t is test_queries[-1]:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for j in range(len(f)): 
          # for i in range(f.shape[0]):
          #   f[i, :] /= np.linalg.norm(f[i, :])
          f[j, :] /= np.linalg.norm(f[j, :])

          X1 = np.insert(f[j],0, 1)
          X2=np.matmul(X1,beta) 
          f[j]=X2
        
        all_queries += [f]
        imgs = []
        mods = []
    all_queries = np.concatenate(all_queries)
    all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    for i in range(10000):
      print('get images=',i,end='\r')
      item = testset[i]
      imgs += [item['source_img_data']]
      mods += [item['mod']['str']]
      if len(imgs) >= opt.batch_size or i == 9999:
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for j in range(len(f)): 
          #for i in range(f.shape[0]):
            #f[i, :] /= np.linalg.norm(f[i, :])
          f[j, :] /= np.linalg.norm(f[j, :])
          X1 = np.insert(f[j],0, 1)
          X2=np.matmul(X1,beta) 
          f[j]=X2
        all_queries += [f]
        imgs = []
        mods = []
      imgs0 += [item['target_img_data']]
      if len(imgs0) >= opt.batch_size or i == 9999:
        imgs0 = torch.stack(imgs0).float()
        imgs0 = torch.autograd.Variable(imgs0)
        imgs0 = model.extract_img_feature(imgs0).data.cpu().numpy()
        all_imgs += [imgs0]
        imgs0 = []
      all_captions += [item['target_caption']]
      all_target_captions += [item['target_caption']]
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out




def testSemantic(all_captions,all_target_captions,OutputofModel,SearchedFeatures):
  # feature normalization
  OutputofModel=tensor(OutputofModel)
  OutputofModel=Variable(OutputofModel,requires_grad=False)
  OutputofModel=np.array(OutputofModel)

  SearchedFeatures=tensor(SearchedFeatures)
  SearchedFeatures=Variable(SearchedFeatures,requires_grad=False)
  SearchedFeatures=np.array(SearchedFeatures)

  for i in range(OutputofModel.shape[0]):
    OutputofModel[i, :] /= np.linalg.norm(OutputofModel[i, :])
  for i in range(SearchedFeatures.shape[0]):
    SearchedFeatures[i, :] /= np.linalg.norm(SearchedFeatures[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(OutputofModel.shape[0])):
    sims = OutputofModel[i:(i+1), :].dot(SearchedFeatures.T)
    
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    
  return out


################# Test by accessing files directly saved before  #########################

def testLoaded(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]
    

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedWithoutModel(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_imagesWithoutModelTrig()
    all_captions = datasets.Features33K().Get_all_captionsWithoutModelTrig()
    all_queries = datasets.Features33K().Get_all_queriesWithoutModelTrig()
    all_target_captions = datasets.Features33K().Get_target_captionsWithoutModelTrig()

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_imagesWithoutModelTrig()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captionsWithoutModelTrig()[:10000]
    all_queries = datasets.Features172K().Get_all_queriesWithoutModelTrig()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captionsWithoutModelTrig()[:10000]
    

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedWithoutModeRegModel(opt, model, testset,reg):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_imagesWithoutModelTrig()
    all_captions = datasets.Features33K().Get_all_captionsWithoutModelTrig()
    all_queries = datasets.Features33K().Get_all_queriesWithoutModelTrig()
    all_target_captions = datasets.Features33K().Get_target_captionsWithoutModelTrig()

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_imagesWithoutModelTrig()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captionsWithoutModelTrig()[:10000]
    all_queries = datasets.Features172K().Get_all_queriesWithoutModelTrig()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captionsWithoutModelTrig()[:10000]

  
  #all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  all_queries =reg.predict(all_queries)
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedRegModel(opt, model, testset,reg):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

  
  all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  all_queries =reg.predict(all_queries)
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedRegModelPlusFFL(opt, model, testset,reg,FFL):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

  
  all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  
  # all_queries =reg.predict(all_queries)
  all_queries=FFL.myforward(torch.FloatTensor(all_queries)).data.cpu().numpy()
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out























def testLoadedRandomForestRegressor(opt, model, testset,reg):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()
    # all_imgs = datasets.Features172K().Get_all_images()[140000:172048]
    
    # all_captions = datasets.Features172K().Get_all_captions()[140000:172048]
    # all_queries1 = datasets.Features172K().Get_all_queries()[140000:172048]
    # all_target_captions = datasets.Features172K().Get_all_captions()[140000:172048]

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

  
  all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  all_queries =reg.predict(all_queries)
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    # if test_queries:
    #   sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedBeta(opt, model, testset,beta):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      # with open (Path1+"\\ERRORtrainLoaded.txt", 'rb') as fp:
      #   ERROR = pickle.load(fp) 
      #   X2=X2+ERROR
      all_queries.append(X2)

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]
    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      # with open (Path1+"\\ERRORtrainLoaded.txt", 'rb') as fp:
      #   ERROR = pickle.load(fp) 
      #   X2=X2+ERROR
        
      all_queries.append(X2)
    
  all_queries= np.array(all_queries)
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out


def testLoadedold(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_imagesold()
    all_captions = datasets.Features33K().Get_all_captionsold()
    all_queries = datasets.Features33K().Get_all_queriesold()
    all_target_captions = datasets.Features33K().Get_target_captionsold()

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_imagesold()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captionsold()[:10000]
    all_queries = datasets.Features172K().Get_all_queriesold()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captionsold()[:10000]
    

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedBetaold(opt, model, testset,beta):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_imagesold()
    all_captions = datasets.Features33K().Get_all_captionsold()
    all_queries1 = datasets.Features33K().Get_all_queriesold()
    all_target_captions = datasets.Features33K().Get_target_captionsold()

    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      # with open (Path1+"\\ERRORtrainLoaded.txt", 'rb') as fp:
      #   ERROR = pickle.load(fp) 
      #   X2=X2+ERROR
      all_queries.append(X2)

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_imagesold()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captionsold()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queriesold()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captionsold()[:10000]
    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      # with open (Path1+"\\ERRORtrainLoaded.txt", 'rb') as fp:
      #   ERROR = pickle.load(fp) 
      #   X2=X2+ERROR
        
      all_queries.append(X2)
    
  all_queries= np.array(all_queries)
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out


def testLoadedRegModelphix(opt, model, testset,reg):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_phixtarget()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_phix()
    all_target_captions = datasets.Features33K().Get_target_captions()

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_phixtarget()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_phix()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

  
  all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  all_queries =reg.predict(all_queries)
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedRandomForestRegressorphix(opt, model, testset,reg):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_phixtarget()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_phix()
    all_target_captions = datasets.Features33K().Get_target_captions()
    # all_imgs = datasets.Features172K().Get_all_images()[140000:172048]
    
    # all_captions = datasets.Features172K().Get_all_captions()[140000:172048]
    # all_queries1 = datasets.Features172K().Get_all_queries()[140000:172048]
    # all_target_captions = datasets.Features172K().Get_all_captions()[140000:172048]

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_phixtarget()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_phix()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

  
  all_queries=all_queries1
  
  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  all_queries =reg.predict(all_queries)
    

    
  all_queries= np.array(all_queries)

  # match test queries to target images, get nearest neighbors
  nn_result = []
  #euc_new_nn_result=[]
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    #euc_new_sims=np.sum(abs(all_imgs-all_queries[i, :]),axis=1)
    # if test_queries:
    #   sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      #euc_new_sims[test_queries[i]['source_img_id']]=10e10
    nn_result.append(np.argsort(-sims[0, :])[:110])
    #euc_new_nn_result.append(np.argsort(euc_new_sims)[:110])

  # compute recalls
  out = []
  
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  #euc_new_nn_result = [[all_captions[nn] for nn in nns] for nns in euc_new_nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    # r = 0.0
    # for i, nns in enumerate(euc_new_nn_result):
    #   if all_target_captions[i] in nns[:k]:
    #     r += 1
    # r /= len(euc_new_nn_result)
    # #out += [('recall_top' + str(k) + '_correct_composition', r)]
    # out.append('EUC:' +str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out








def testLoadedNLP(opt, model, testset, model2):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    all_queries=(torch.Tensor(all_queries))
    all_queries=model2.myforward(all_queries).data.cpu().numpy()


  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

    all_queries=(torch.Tensor(all_queries))
    all_queries=model2.myforward(all_queries).data.cpu().numpy()
    

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedBetaWNLP(opt, model, testset,beta, model2):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      all_queries.append(X2)

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]
    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      all_queries.append(X2)
    
  all_queries= np.array(all_queries)

  all_queries=(torch.Tensor(all_queries))
  all_queries=model2.myforward(all_queries).data.cpu().numpy()
  # feature normalization
  # for i in range(all_queries.shape[0]):
  #   all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testLoadedNLPwBeta(opt, model, testset,beta, model2):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_queries1=[]
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries1 = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

    all_queries1=(torch.Tensor(all_queries1))
    all_queries1=model2.myforward(all_queries1).data.cpu().numpy()

    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      all_queries.append(X2)

    

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()[:10000]
    
    all_captions = datasets.Features172K().Get_all_captions()[:10000]
    all_queries1 = datasets.Features172K().Get_all_queries()[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()[:10000]

    all_queries1=(torch.Tensor(all_queries1))
    all_queries1=model2.myforward(all_queries1).data.cpu().numpy()

    for j in range(len(all_queries1)): 
      all_queries1[j, :] /= np.linalg.norm(all_queries1[j, :])
      X1 = np.insert(all_queries1[j],0, 1)
      X2=np.matmul(X1,beta) 
      all_queries.append(X2)
    
  all_queries= np.array(all_queries)
  
  
  # feature normalization
  # for i in range(all_queries.shape[0]):
  #   all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out







def testLoaded_NLP(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    
    all_imgs = datasets.Features33K().Get_all_images()
    all_captions = datasets.Features33K().Get_all_captions()
    all_queries = datasets.Features33K().Get_all_queries()
    all_target_captions = datasets.Features33K().Get_target_captions()

  else:
    # use training queries to approximate training retrieval performance
    all_imgs = datasets.Features172K().Get_all_images()#[:10000]
    all_captions = datasets.Features172K().Get_all_captions()#[:10000]
    all_queries = datasets.Features172K().Get_all_queries()#[:10000]
    all_target_captions = datasets.Features172K().Get_all_captions()#[:10000]
    
  modelNLR=main2.NLR2(all_queries.shape[1],all_imgs.shape[1],700)
  modelNLR.load_state_dict(torch.load(Path1+r'\NLPMohamed3.pth'))
  modelNLR.eval()
  all_queries=torch.from_numpy(all_queries)
  

  # for t in range(int(len(all_queries))):
  #   print('get testdata=',t,end='\r')
  #   f=all_queries[t]
  #   all_queries[t] = modelNLR.myforward(f)

  all_queries = modelNLR.myforward(all_queries)
  
  #all_queries.detach().numpy()
  all_queries = torch.tensor(all_queries,requires_grad=False)
  all_queries=np.array(all_queries)

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testWbeta(opt, model, testset,beta):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()
 

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in tqdm(test_queries):
      imgs += [testset.get_img(t['source_img_id'])]
      mods += [t['mod']['str']]
      if len(imgs) >= opt.batch_size or t is test_queries[-1]:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for j in range(len(f)): 
          # for i in range(f.shape[0]):
          #   f[i, :] /= np.linalg.norm(f[i, :])
          f[j, :] /= np.linalg.norm(f[j, :])

          X1 = np.insert(f[j],0, 1)
          X2=np.matmul(X1,beta) 
          f[j]=X2
        
        all_queries += [f]
        imgs = []
        mods = []
    all_queries = np.concatenate(all_queries)
    all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    for i in range(10000):
      print('get images=',i,end='\r')
      item = testset[i]
      imgs += [item['source_img_data']]
      mods += [item['mod']['str']]
      if len(imgs) >= opt.batch_size or i == 9999:
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for j in range(len(f)): 
          #for i in range(f.shape[0]):
            #f[i, :] /= np.linalg.norm(f[i, :])
          f[j, :] /= np.linalg.norm(f[j, :])
          X1 = np.insert(f[j],0, 1)
          X2=np.matmul(X1,beta) 
          f[j]=X2
        all_queries += [f]
        imgs = []
        mods = []
      imgs0 += [item['target_img_data']]
      if len(imgs0) >= opt.batch_size or i == 9999:
        imgs0 = torch.stack(imgs0).float()
        imgs0 = torch.autograd.Variable(imgs0)
        imgs0 = model.extract_img_feature(imgs0).data.cpu().numpy()
        all_imgs += [imgs0]
        imgs0 = []
      all_captions += [item['target_caption']]
      all_target_captions += [item['target_caption']]
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testNLP(opt, model, testset,model2):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()
 

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in tqdm(test_queries):
      imgs += [testset.get_img(t['source_img_id'])]
      mods += [t['mod']['str']]
      if len(imgs) >= opt.batch_size or t is test_queries[-1]:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for i in range(f.shape[0]):
          f[i, :] /= np.linalg.norm(f[i, :])
        f =np.insert(f,0, 1)
        f=np.expand_dims(f, axis=0)
        f=torch.from_numpy(f)
        
        f=model2.myforward(f).data.cpu().numpy()


        all_queries += [f]
        imgs = []
        mods = []
    all_queries = np.concatenate(all_queries)
    all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    for i in range(10000):
      print('get images=',i,end='\r')
      item = testset[i]
      imgs += [item['source_img_data']]
      mods += [item['mod']['str']]
      if len(imgs) >= opt.batch_size or i == 9999:
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        for i in range(f.shape[0]):
          f[i, :] /= np.linalg.norm(f[i, :])
        f =np.insert(f,0, 1)
        f=np.expand_dims(f, axis=0)
        f=torch.from_numpy(f)
        
        f=model2.myforward(f).data.cpu().numpy()


        all_queries += [f]
        imgs = []
        mods = []
      imgs0 += [item['target_img_data']]
      if len(imgs0) >= opt.batch_size or i == 9999:
        imgs0 = torch.stack(imgs0).float()
        imgs0 = torch.autograd.Variable(imgs0)
        imgs0 = model.extract_img_feature(imgs0).data.cpu().numpy()
        all_imgs += [imgs0]
        imgs0 = []
      all_captions += [item['target_caption']]
      all_target_captions += [item['target_caption']]
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  # feature normalization
  # for i in range(all_queries.shape[0]):
  #   all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def testWbetaWsaveddata(opt, model, testset,beta,savedtrain,savedtest):
  """Tests a model over the given testset."""
  model.eval()
  
  test_queries = testset.get_test_queries()
 

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in range(len(savedtest)):
      print('get testdata=',t,end='\r')
      f=savedtest[t]['SourceTrig']
      f=np.expand_dims(f, axis=0)
      for j in range(len(f)): 
        
        f[j, :] /= np.linalg.norm(f[j, :])
        X1 = np.insert(f[j],0, 1)
        X2=np.matmul(X1,beta) 
        f[j]=X2
      
      all_queries += [f]
      imgs = []
      mods = []

    all_queries = np.concatenate(all_queries)
    all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    
    
    for i in range(10000):
      print('get images=',i,end='\r')
      item = testset[i]
      f=savedtrain[i]['SourceTrig']
      f=np.expand_dims(f, axis=0)
      for j in range(len(f)): 
          
        f[j, :] /= np.linalg.norm(f[j, :])
        X1 = np.insert(f[j],0, 1)
        X2=np.matmul(X1,beta) 
        f[j]=X2
        
      all_queries += [f]
      imgs = []
      mods = []
      imgs0 += [savedtrain[i]['TargetData']]
      all_imgs += [imgs0]
      imgs0 = []
      all_captions += [item['target_caption']]
      all_target_captions += [item['target_caption']]
      f=[]
    
    
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def test_and_save(opt, model, testset):
  """Tests a model over the given testset."""
  model.eval()
  test_queries = testset.get_test_queries()

  all_imgs = []
  all_captions = []
  all_queries = []
  all_target_captions = []
  all_captions=[]
  if test_queries:
    # compute test query features
    imgs = []
    mods = []
    for t in tqdm(test_queries):
      imgs += [testset.get_img(t['source_img_id'])]
      all_captions += [t['source_caption']]
      all_target_captions += [t['target_caption']]
      mods += [t['mod']['str']]
      if len(imgs) >= opt.batch_size or t is test_queries[-1]:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)#.cuda()
        f = model.compose_img_text(imgs, mods).data.cpu().numpy()
        all_queries += [f]
        imgs = []
        mods = []
    all_queries = np.concatenate(all_queries)
    #all_target_captions = [t['target_caption'] for t in test_queries]

    # compute all image features
    imgs = []
    for i in tqdm(range(len(testset.imgs))):
      imgs += [testset.get_img(i)]
      if len(imgs) >= opt.batch_size or i == len(testset.imgs) - 1:
        if 'torch' not in str(type(imgs[0])):
          imgs = [torch.from_numpy(d).float() for d in imgs]
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)#.cuda()
        imgs = model.extract_img_feature(imgs).data.cpu().numpy()
        all_imgs += [imgs]
        imgs = []
    all_imgs = np.concatenate(all_imgs)
    all_captions = [img['captions'][0] for img in testset.imgs]

  else:
    # use training queries to approximate training retrieval performance
    imgs0 = []
    imgs = []
    mods = []
    for i in range(len(testset)):
      
      item = testset[i]
      imgs += [item['source_img_data']]
      mods += [item['mod']['str']]
      if len(imgs) >= opt.batch_size or i == 9999:
        imgs = torch.stack(imgs).float()
        imgs = torch.autograd.Variable(imgs)
        f = model.compose_img_text(imgs, mods).data.cpu().numpy() #.cuda()
        all_queries += [f]
        imgs = []
        mods = []
      imgs0 += [item['target_img_data']]
      if len(imgs0) >= opt.batch_size or i == 9999:
        imgs0 = torch.stack(imgs0).float()
        imgs0 = torch.autograd.Variable(imgs0)
        imgs0 = model.extract_img_feature(imgs0).data.cpu().numpy() #.cuda()
        all_imgs += [imgs0]
        imgs0 = []
      all_captions += [item['source_caption']]
      all_target_captions += [item['target_caption']]
    all_imgs = np.concatenate(all_imgs)
    all_queries = np.concatenate(all_queries)

  if test_queries:
   with open(Path1+r"/"+'test_test_queries.pkl', 'wb') as fp:
    pickle.dump(test_queries, fp)
   with open(Path1+r"/"+'test_all_queries.pkl', 'wb') as fp:
    pickle.dump(all_queries, fp)

   with open(Path1+r"/"+'test_all_imgs.pkl', 'wb') as fp:
    pickle.dump(all_imgs, fp)
   with open(Path1+r"/"+'test_all_captions.pkl', 'wb') as fp:
    pickle.dump(all_captions, fp)
   with open(Path1+r"/"+'test_all_target_captions.pkl', 'wb') as fp:
    pickle.dump(all_target_captions, fp)
  else:
   with open(Path1+r"/"+'test_queries172k.pkl', 'wb') as fp:
    pickle.dump(test_queries, fp)

   with open(Path1+r"/"+'all_queries172k.pkl', 'wb') as fp:
    pickle.dump(all_queries, fp)
   with open(Path1+r"/"+'all_imgs172k.pkl', 'wb') as fp:
    pickle.dump(all_imgs, fp)
   with open(Path1+r"/"+'all_captions172k.pkl', 'wb') as fp:
    pickle.dump(all_captions, fp)
   with open(Path1+r"/"+'all_target_captions172k.pkl', 'wb') as fp:
    pickle.dump(all_target_captions, fp)




  # feature normalization
  for i in range(all_queries.shape[0]):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(all_imgs.shape[0]):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  for i in tqdm(range(all_queries.shape[0])):
    sims = all_queries[i:(i+1), :].dot(all_imgs.T)
    if test_queries:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    nn_result.append(np.argsort(-sims[0, :])[:110])

  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

    if opt.dataset == 'mitstates':
      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[0] in [c.split()[0] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_adj', r)]

      r = 0.0
      for i, nns in enumerate(nn_result):
        if all_target_captions[i].split()[1] in [c.split()[1] for c in nns[:k]]:
          r += 1
      r /= len(nn_result)
      out += [('recall_top' + str(k) + '_correct_noun', r)]

  return out

def test_on_saved(test_train,normal_beta,create_load,filename,normal_normalize,sz,dot_eucld):
  # test_queries:
  if test_train==0:
   with open(Path1+r"/"+'test_test_queries.pkl', 'rb') as fp:
    test_queries=pickle.load( fp)

   with open(Path1+r"/"+'test_all_queriesG.pkl', 'rb') as fp:
    all_queries=pickle.load( fp)
   with open(Path1+r"/"+'test_all_imgsG.pkl', 'rb') as fp:
    all_imgs=pickle.load( fp)
   with open(Path1+r"/"+'test_all_target_captionsG.pkl', 'rb') as fp:
    all_captions=pickle.load( fp)
   with open(Path1+r"/"+'test_all_target_captionsG.pkl', 'rb') as fp:
    all_target_captions=pickle.load( fp)
  else:
   with open(Path1+r"/"+'test_queries1806172k.pkl', 'rb') as fp:
    test_queries=pickle.load( fp)

   with open(Path1+r"/"+'all_queries1806172k.pkl', 'rb') as fp:
    all_queries=pickle.load( fp)
   with open(Path1+r"/"+'all_imgs1806172k.pkl', 'rb') as fp:
    all_imgs=pickle.load( fp)
   with open(Path1+r"/"+'all_captions1806172k.pkl', 'rb') as fp:
    all_captions=pickle.load( fp)
   with open(Path1+r"/"+'all_target_captions1806172k.pkl', 'rb') as fp:
    all_target_captions=pickle.load( fp)
  if (normal_beta==1 ):
    if(create_load==0):
    #################################
      new_all_queries=np.zeros((all_queries.shape[0],all_queries.shape[1]+1))
      for i in range(all_queries.shape[0]):
        f=all_queries[i,:]
        if (normal_normalize==1):
          f/=np.linalg.norm(f)
        f=np.insert(f,0,1)
        new_all_queries[i,:]=f
      if (normal_normalize==1):
        for i in range(all_imgs.shape[0]):
          all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])
      
      new_all_queriest=new_all_queries.transpose()
      X1=np.matmul(new_all_queriest,new_all_queries)  
      X2=np.linalg.inv(X1)
      X3=np.matmul(X2,new_all_queriest)  
      beta=np.matmul(X3,all_imgs) 
      new_all_queries=[]
      new_all_queriest=[]
     #################################
      with open(Path1+r"/"+filename, 'wb') as fp:
        pickle.dump( beta, fp)
    else:
      with open(Path1+r"/"+filename, 'rb') as fp:
        beta=pickle.load( fp)
    for t in range(int(len(all_queries)/sz)):
      if (t%100==0):
        print('get testdata=',t,end='\r')
      f=all_queries[t,:]
      if (normal_normalize==1):
        f/=np.linalg.norm(f)
       
      f=np.insert(f,0,1)
      
      X2=np.matmul(f,beta) 
        
      all_queries[t,:] = X2
      
    
    
    
  # feature normalization
  for i in range(int(all_queries.shape[0]/sz)):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(int(all_imgs.shape[0]/sz)):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  sims=np.zeros((1,int(all_imgs.shape[0]/sz)))

  for i in tqdm(range(int(all_queries.shape[0]/sz))):
    if (dot_eucld==0):
      sims = all_queries[i:(i+1), :].dot(all_imgs[:int(all_imgs.shape[0]/sz)].T)
    else:
      sims[0,:]=np.sum(abs(all_imgs[:int(all_imgs.shape[0]/sz),:]-all_queries[i, :]),axis=1)
      #for j in range(int(all_imgs.shape[0]/sz)):
      #  sims[0,j] =distance.euclidean( all_queries[i, :],all_imgs[j,:])


    if test_train==0:
      if (dot_eucld==0):
        sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      else:
        sims[0, test_queries[i]['source_img_id']] = 10e10  # remove query image
    if (dot_eucld==0):
      nn_result.append(np.argsort(-sims[0, :])[:110])
    else:
      nn_result.append(np.argsort(sims[0, :])[:110])

  all_imgs=[]
  all_queries=[]
  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

  print(out)  
  
 
  return out

def train_network_on_saved(test_train,create_load,normal_normalize,filename,sz,dot_eucld):
  if test_train==0:
   with open(Path1+r"/"+'test_test_queries.pkl', 'rb') as fp:
    test_queries=pickle.load( fp)

   with open(Path1+r"/"+'test_all_queriesG.pkl', 'rb') as fp:
    all_queries=pickle.load( fp)
   with open(Path1+r"/"+'test_all_imgsG.pkl', 'rb') as fp:
    all_imgs=pickle.load( fp)
   with open(Path1+r"/"+'test_all_target_captionsG.pkl', 'rb') as fp:
    all_captions=pickle.load( fp)
   with open(Path1+r"/"+'test_all_target_captionsG.pkl', 'rb') as fp:
    all_target_captions=pickle.load( fp)
  else:
   with open(Path1+r"/"+'test_queries172k.pkl', 'rb') as fp:
    test_queries=pickle.load( fp)

   with open(Path1+r"/"+'all_queries172k.pkl', 'rb') as fp:
    all_queries=pickle.load( fp)
   with open(Path1+r"/"+'all_imgs172k.pkl', 'rb') as fp:
    all_imgs=pickle.load( fp)
   with open(Path1+r"/"+'all_captions172k.pkl', 'rb') as fp:
    all_captions=pickle.load( fp)
   with open(Path1+r"/"+'all_target_captions172k.pkl', 'rb') as fp:
    all_target_captions=pickle.load( fp)
    
    #################################
      
    
    
    
  # feature normalization
  for i in range(int(all_queries.shape[0]/sz)):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(int(all_imgs.shape[0]/sz)):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  sims=np.zeros((1,int(all_imgs.shape[0]/sz)))

  for i in tqdm(range(int(all_queries.shape[0]/sz))):
    if (dot_eucld==0):
      sims = all_queries[i:(i+1), :].dot(all_imgs[:int(all_imgs.shape[0]/sz)].T)
    else:
      sims[0,:]=np.sum(abs(all_imgs[:int(all_imgs.shape[0]/sz),:]-all_queries[i, :]),axis=1)
      #for j in range(int(all_imgs.shape[0]/sz)):
      #  sims[0,j] =distance.euclidean( all_queries[i, :],all_imgs[j,:])


    if test_train==0:
      if (dot_eucld==0):
        sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
      else:
        sims[0, test_queries[i]['source_img_id']] = 10e10  # remove query image
    if (dot_eucld==0):
      nn_result.append(np.argsort(-sims[0, :])[:105])
    else:
      nn_result.append(np.argsort(sims[0, :])[:105])

  all_imgs=[]
  all_queries=[]
  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

  print(out)  
  
 
  return out

def Phase2_networks_tests(test_train,all_queries):
  
  if test_train==0:
   test_queries = datasets.Fashion200k(path=Path1,
        split='train',
        transform=torchvision.transforms.Compose([
            torchvision.transforms.Resize(224),
            torchvision.transforms.CenterCrop(224),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize([0.485, 0.456, 0.406],
                                              [0.229, 0.224, 0.225])
        ])).test_queries
   all_imgs = datasets.Features172K().Get_phixtarget()
   all_captions= datasets.Features172K().Get_all_captions()
   all_target_captions=datasets.Features172K().Get_all_captions()

   
  else:
   test_queries = datasets.Fashion200k(path=Path1,
        split='test',
        transform=torchvision.transforms.Compose([
            torchvision.transforms.Resize(224),
            torchvision.transforms.CenterCrop(224),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize([0.485, 0.456, 0.406],
                                              [0.229, 0.224, 0.225])
        ])).test_queries
   all_imgs=datasets.Features33K().Get_all_images()
   all_captions=datasets.Features33K().Get_target_captions()
   all_target_captions=datasets.Features33K().Get_target_captions()
   
    #################################
      
  # feature normalization
  all_imgs=np.concatenate(all_imgs)
  for i in range(int(all_queries.shape[0])):
    all_queries[i, :] /= np.linalg.norm(all_queries[i, :])
  for i in range(int(all_imgs.shape[0])):
    all_imgs[i, :] /= np.linalg.norm(all_imgs[i, :])

  # match test queries to target images, get nearest neighbors
  nn_result = []
  sims=np.zeros((1,int(all_imgs.shape[0])))

  for i in tqdm(range(int(all_queries.shape[0]))):
    sims = all_queries[i:(i+1), :].dot(all_imgs[:int(all_imgs.shape[0])].T)
    
    if test_train==0:
      sims[0, test_queries[i]['source_img_id']] = -10e10  # remove query image
    
    nn_result.append(np.argsort(-sims[0, :])[:105])
    
  all_imgs=[]
  all_queries=[]
  # compute recalls
  out = []
  nn_result = [[all_captions[nn] for nn in nns] for nns in nn_result]
  
  for k in [1, 5, 10, 50, 100]:
    r = 0.0
    for i, nns in enumerate(nn_result):
      if all_target_captions[i] in nns[:k]:
        r += 1
    r /= len(nn_result)
    #out += [('recall_top' + str(k) + '_correct_composition', r)]
    out.append(str(k) + ' ---> '+ str(r*100))

  print(out)  
  
 
  return out
