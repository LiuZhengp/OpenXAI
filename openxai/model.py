import torch
from torch import nn
import torch.nn.functional as F
import numpy as np
import os
import requests

activation_functions = {'relu': nn.ReLU(), 'leaky_relu': nn.LeakyReLU(),
                        'sigmoid': nn.Sigmoid(), 'tanh': nn.Tanh()}

dataverse_prefix = 'https://dataverse.harvard.edu/api/access/datafile/'
dataverse_ids = {
    'lr': {
        'adult': '8550955', 'compas': '8550949', 'gaussian': '8550960', 'german': '8550945',
        'gmsc': '8550948', 'heart': '8550956', 'heloc': '8550950', 'pima': '8550959'
    },
    'ann': {
        'adult': '8550958', 'compas': '8550951', 'gaussian': '8550957', 'german': '8550946',
        'gmsc': '8550947', 'heart': '8550954', 'heloc': '8550952', 'pima': '8550953'
    },
}

def LoadModel(data_name: str, ml_model, pretrained: bool = True):
    """
    Load a pretrained model
    :param data_name: string with name of dataset
    :param ml_model: string with name of model; 'lr' or 'ann'
    :param pretrained: boolean, whether to load a pretrained model
    :return: model
    """
    if pretrained:
        model_path = './models/pretrained/'
        os.makedirs(model_path, exist_ok=True)
        if data_name in dataverse_ids[ml_model]:
            r = requests.get(dataverse_prefix + dataverse_ids[ml_model][data_name], allow_redirects=True)
            model_filename = f'{ml_model}_{data_name}.pt'
            open(model_path+model_filename, 'wb').write(r.content)
            state_dict = torch.load(model_path+model_filename, map_location=torch.device('cpu'))
            num_features = next(iter(state_dict.values())).shape[1]
            if ml_model == 'ann':
                model = ArtificialNeuralNetwork(num_features, [100, 100])
            elif ml_model == 'lr':
                model = LogisticRegression(num_features)
            model.load_state_dict(state_dict)
        else:
            raise NotImplementedError(
                f'The current version of >LoadModel< does not support this data set for {ml_model.upper()} models.')
    else:
        raise NotImplementedError(
             'The current version of >LoadModel< does not support training a ML model from scratch, yet.')
    return model


class LogisticRegression(nn.Module):
    def __init__(self, input_dim, n_class = 2):
        '''
        Initializes the logistic regression model
        :param input_dim: int, number of features
        :param n_class: int, number of classes
        '''
        super().__init__()
        self.name = 'LogisticRegression'
        self.abbrv = 'lr'

        # Construct layers
        self.input_dim = input_dim
        self.n_class = n_class
        self.linear = nn.Linear(self.input_dim, self.n_class)
        
    def return_ground_truth_importance(self):
        return self.linear.weight[1, :] - self.linear.weight[0, :]
        
    def forward(self, x):
        return F.softmax(self.linear(x), dim=-1)
    
    def predict_with_logits(self, x):
        return self.linear(x)
    
    def predict(self, data):
        """
        Predict method required for CFE-Models
        :param data: torch or list
        :return: numpy array of predictions
        """
        if not torch.is_tensor(data):
            input = torch.from_numpy(np.array(data)).float()
        else:
            input = torch.squeeze(data)
            
        output = self.forward(input).detach().numpy()

        return output

class ArtificialNeuralNetwork(nn.Module):
    def __init__(self, input_dim, hidden_layers, n_class = 2, activation = 'relu'):
        """
        Initializes the artificial neural network model
        :param input_dim: int, number of features
        :param hidden_layers: list of int, number of neurons in each hidden layer
        :param n_class: int, number of classes
        """
        super().__init__()
        self.name = 'ArtificialNeuralNetwork'
        self.abbrv = 'ann'
        
        # Construct layers
        model_layers = []
        previous_layer = input_dim
        for layer in hidden_layers:
            model_layers.append(nn.Linear(previous_layer, layer))
            model_layers.append(activation_functions[activation])
            previous_layer = layer
        model_layers.append(nn.Linear(previous_layer, n_class))
        self.network = nn.Sequential(*model_layers)
    
    def predict_layer(self, x, hidden_layer_idx=0, post_act=True):
        """
        Returns the representation of the input tensor at the specified layer
        :param x: torch.tensor, input tensor
        :param layer: int, layer number
        :param post_act: bool, whether to return the activations before or after the activation function
        """
        if hidden_layer_idx >= len(self.network) // 2:
            raise ValueError(f'The model has only {len(self.network) // 2} hidden layers, but hidden layer {hidden_layer_idx} was requested (indexing starts at 0).')
        
        network_idx = 2 * hidden_layer_idx + int(post_act)
        return self.network[:network_idx+1](x)
    
    def forward(self, x):
        return F.softmax(self.network(x), dim=-1)
    
    def predict_with_logits(self, x):
        return self.network(x)
    
    def predict_proba(self, x):
        # Currently used by SHAP
        input = x if torch.is_tensor(x) else torch.from_numpy(np.array(x))
        return self.forward(input.float()).detach().numpy()
    
    def predict(self, x):
        # Currently used by LIME
        input = torch.squeeze(x) if torch.is_tensor(x) else torch.from_numpy(np.array(x))
        return self.forward(input.float()).detach().numpy()
