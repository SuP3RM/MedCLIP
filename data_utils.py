from glob import glob
import random
from PIL import Image
# import numpy as np
import pandas as pd
import os # , cv2,itertools
from torch.utils.data import Dataset, random_split
import torch

LESION_TYPE = {
        'nv': 'Melanocytic nevi',
        'mel': 'dermatofibroma',
        'bkl': 'Benign keratosis-like lesions ',
        'bcc': 'Basal cell carcinoma',
        'akiec': 'Actinic keratoses',
        'vasc': 'Vascular lesions',
        'df': 'Dermatofibroma'
    }

# here are 15 classes (14 diseases, and one for "No findings"). 
# Images can be classified as "No findings" or one or more disease classes:
NIH_CLASS_TYPES = [
    'Atelectasis',
    'Consolidation',
    'Infiltration',
    'Pneumothorax',
    'Edema',
    'Emphysema',
    'Fibrosis',
    'Effusion',
    'Pneumonia',
    'Pleural_thickening',
    'Cardiomegaly',
    'Nodule',
    'Mass',
    'Hernia',
    'No Finding'
]


def load_dataset(name, transform=None, data_dir=None):
    """
    Loads the specified dataset (either HAM10000 or NIH) from
    data_dir, applying transform.
    
    Returns a training and testing/val dataset
    """
    if name == "HAM10000":
        if data_dir is None:
            data_dir = "data/ham10000"
            
        return load_ham10000_dataset(data_dir, transform, True)
    elif name == "NIH":
        # TODO: write function to load NIH dataset. We probably need to modify this stuff a bit bc NIH give train/val/test but HAM is only one split.
        if data_dir is None:
            data_dir = "data/nih"
            
        raise NotImplementedError("This dataset isn't implemented")
    else:
        raise ValueError("expected either 'HAM10000' or 'NIH', but received " + name)

def load_ham10000_dataset(data_dir="data/ham10000", transform=None, split=True):
    print("Loading HAM10000 dataset...")
    df = get_dataframe(data_dir)
    dataset = HAM10000(df, transform)
    if split:
        train_size = int(0.9 * len(dataset))
        test_size = len(dataset) - train_size
        train_dataset, test_dataset = random_split(dataset, [train_size, test_size])
        return train_dataset, test_dataset
    else:
        return dataset
    


class HAM10000(Dataset):
    def __init__(self, df, transform=None):
        self.df = df
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):
        # Load data and get label
        X = Image.open(self.df['path'][index])
        y = torch.tensor(int(self.df['cell_type_idx'][index]))

        if self.transform:
            X = self.transform(X)

        return X, y

def get_dataframe(data_dir):
    # https://www.kaggle.com/code/xinruizhuang/skin-lesion-classification-acc-90-pytorch
    all_image_path = glob(os.path.join(data_dir, '*', '*.jpg'))
    imageid_path_dict = {os.path.splitext(os.path.basename(x))[0]: x for x in all_image_path}
    df_original = pd.read_csv(os.path.join(data_dir, 'HAM10000_metadata.csv'))
    df_original['path'] = df_original['image_id'].map(imageid_path_dict.get)
    df_original['cell_type'] = df_original['dx'].map(LESION_TYPE.get)
    df_original['cell_type_idx'] = pd.Categorical(df_original['cell_type']).codes
    return df_original

class NIHDataset(Dataset):
    def __init__(self, csv_file, root_dir, transform=None):
        """
        Args:
            csv_file (string): Path to the csv file with annotations.
            root_dir (string): Directory with all the images.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.root_dir = root_dir
        self.transform = transform
        self.dataframe = self.get_dataframes(csv_file)

    def __len__(self):
        return len(self.dataframe)
    
    def __getitem__(self, idx):
        img_name = self.dataframe.iloc[idx, 0]  # Use the full path directly
        image = Image.open(img_name).convert('RGB')

        labels = self.dataframe.iloc[idx, 1]
        label_tensor = self.convert_labels_to_tensor(labels)

        image = self.transform(image)  # Apply the transform

        return image, label_tensor

    
    def convert_labels_to_tensor(self, labels):
        """
        Converts labels to tensor
        """
        label_tensor = torch.zeros(len(NIH_CLASS_TYPES))
        for label in labels:  # Directly iterate over labels if it's already a list
            if label in NIH_CLASS_TYPES:
                label_tensor[NIH_CLASS_TYPES.index(label)] = 1
        return label_tensor


    
    def get_dataframes(self, csv_file):
        print("Loading NIH dataset...", csv_file)
        print("Loading images from...", self.root_dir)
        all_image_path = glob(os.path.join(self.root_dir, '*.png'))
        # print('all_image_path: ', all_image_path)

        # Ensure the keys include the file extension to match the 'Image Index' in the CSV
        image_id_path_dict = {os.path.splitext(os.path.basename(x))[0] + '.png': x for x in all_image_path}
        # print('image_id_path_dict: ', image_id_path_dict)

        df_original = pd.read_csv(csv_file)

        # Debugging: Print a few values from the CSV to check their format
        # print('CSV Image Index sample:', df_original['Image Index'].head())

        df_original['path'] = df_original['Image Index'].map(image_id_path_dict.get)
        # print('Mapped paths:', df_original['path'].head())

        # df_original['Finding Labels'] = df_original['Finding Labels'].map(lambda x: x.replace('No Finding', 'No_Finding'))
        df_original['Finding Labels'] = df_original['Finding Labels'].map(lambda x: x.split('|'))
        return df_original[['path', 'Finding Labels']]


def load_nih_dataset_split(data_dir="data/nih/", transform=None):
    print("Selecting random image directory...")
    # load csv file
    csv_file_location = os.path.join(data_dir, "Data_Entry_2017.csv")
    print(f"Loading csv file from {csv_file_location}")

    # load dataset
    # path ex: data\nih\images\00001336_000.png
    dataset_location = os.path.join(data_dir, "images")
    print(f"Loading dataset from {dataset_location}")
    Dataset = NIHDataset(csv_file_location, dataset_location, transform)
    print(f"Original Dataset length: {Dataset.__len__()}")

    # split dataset
    train_size = int(0.8 * len(Dataset))
    test_size = len(Dataset) - train_size
    train_dataset, test_dataset = random_split(Dataset, [train_size, test_size])
    print(f"Train dataset length: {train_dataset.__len__()}")
    print(f"Test dataset length: {test_dataset.__len__()}")
    # print(f"Exmaple of train dataset: {train_dataset.__getitem__(0)}")
    return train_dataset, test_dataset