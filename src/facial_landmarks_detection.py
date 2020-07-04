import os
import cv2
import numpy as np
import logging
from openvino.inference_engine import IENetwork, IECore

class FacialLandmarksDetection:
    '''
    Class for the Face Detection Model.
    '''
    def __init__(self, model_name, device='CPU', threshold=0.60,  extensions=None):

        self.model_weights = model_name+'.bin'
        self.model_structure = model_name+'.xml'
        self.device = device
        self.threshold = threshold
        self.extension = extensions
        self.plugin = None
        self.exec_network = None
        self.network = None

        try:
            self.model = IENetwork(self.model_structure, self.model_weights)
        except Exception as e:
            raise ValueError("Could not Initialise the network. Have you enterred the correct model path?")

        self.input_name=next(iter(self.model.inputs))
        self.input_shape=self.model.inputs[self.input_name].shape
        self.output_name=next(iter(self.model.outputs))
        self.output_shape=self.model.outputs[self.output_name].shape


    def load_model(self):

        self.plugin = IECore()
        self.network = self.plugin.read_network(model=self.model_structure, weights=self.model_weights)
        
        if not self.check_model():
            exit(1)
        
        self.exec_network = self.plugin.load_network(network=self.model, device_name=self.device, num_requests=1)

    def predict(self, image):

        input_img = self.preprocess_input(image)
        input_dict={self.input_name: input_img}  
        
        h, w = image.shape[:2]
        
        infer_request_handle = self.exec_network.start_async(request_id=0, inputs=input_dict)
        infer_status = infer_request_handle.wait()

        if infer_status == 0:
            outputs = infer_request_handle.outputs[self.output_name]
            coords = self.preprocess_output(outputs)

            coords = coords* np.array([w, h, w, h])
            coords = coords.astype(np.int32)
            
            (lefteye_x, lefteye_y, righteye_x, righteye_y) = coords

            le_xmin = lefteye_x - 10
            le_ymin = lefteye_y - 10
            le_xmax = lefteye_x + 10
            le_ymax = lefteye_y + 10
            
            re_xmin = righteye_x - 10
            re_ymin = righteye_y - 10
            re_xmax = righteye_x + 10
            re_ymax = righteye_y + 10
        
            left_eye =  image[le_ymin:le_ymax, le_xmin:le_xmax]
            right_eye = image[re_ymin:re_ymax, re_xmin:re_xmax]
            eye_coords = [[le_xmin,le_ymin,le_xmax,le_ymax], [re_xmin,re_ymin,re_xmax,re_ymax]]

            return left_eye, right_eye, eye_coords

    def check_model(self):

        supported_layers = self.plugin.query_network(network=self.network, device_name=self.device)
        unsupported_layers = [layer for layer in self.network.layers.keys() if layer not in supported_layers]
        if len(unsupported_layers) > 0:
            logging.info("unsupported layers found:{}".format(unsupported_layers))
            if not self.extensions:
                logging.info("Adding cpu_extension")
                self.plugin.add_extension(self.extensions, self.device)
                supported_layers = self.plugin.query_network(network = self.network, device_name=self.device)
                unsupported_layers = [l for l in self.network.layers.keys() if l not in supported_layers]
                if len(unsupported_layers)!=0:
                    logging.info("After adding the extension still unsupported layers found")
                    return False
                logging.info("After adding the extension the issue is resolved")
            else:
                logging.info("Give the path of cpu extension")
                return False
        logging.info("All layers are supported for " + self.model_structure)

        return True 

    def preprocess_input(self, image):
        
        image = cv2.resize(image, (self.input_shape[3], self.input_shape[2]))
        image = image.transpose((2,0,1))
        image = image.reshape(1, 3, self.input_shape[2], self.input_shape[3])
        return image

    def preprocess_output(self, outputs):

        #out = outputs[self.output_name][0]
        
        left_eye_x_coordinate  = outputs[0][0].tolist()[0][0]
        left_eye_y_coordinate  = outputs[0][1].tolist()[0][0]
        right_eye_x_coordinate  = outputs[0][2].tolist()[0][0]
        right_eye_y_coordinate  = outputs[0][3].tolist()[0][0]

        return (left_eye_x_coordinate , left_eye_y_coordinate , right_eye_x_coordinate , right_eye_y_coordinate )
