import numpy as np
import cPickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.core.protobuf import saver_pb2
import cv2

from model import ENet_model

#project_dir = "/home/fregu856/segmentation/"
project_dir = "/root/segmentation/"
data_dir = project_dir + "data/"

img_height = 256
img_width = 512
no_of_classes = 20

def evaluate_on_val(batch_size, sess):
    """
    - DOES:
    """

    # load the val data from disk:
    val_trainId_label_paths = cPickle.load(open(data_dir + "val_trainId_label_paths.pkl"))
    val_img_paths = cPickle.load(open(data_dir + "val_img_paths.pkl"))

    batch_imgs = np.zeros((batch_size, img_height, img_width, 3), dtype=np.float32)
    batch_onehot_labels = np.zeros((batch_size, img_height, img_width, no_of_classes), dtype=np.float32)
    #batch_onehot_labels = np.zeros((batch_size, img_height, img_width), dtype=np.int32)
    layer_idx = np.arange(img_height).reshape(img_height, 1)
    component_idx = np.tile(np.arange(img_width), (img_height, 1))
    for i in range(batch_size):
        # read the next img:
        img = cv2.imread(val_img_paths[i], -1)
        cv2.imwrite("img_" + str(i) + ".png", img)
        batch_imgs[i] = img

        trainId_label = cv2.imread(val_trainId_label_paths[i], -1)
        # onehot_label = tf.one_hot(indices=trainId_label, depth=no_of_classes)
        # onehot_label = sess.run(onehot_label) # (convert to numpy array)
        onehot_label = np.zeros((img_height, img_width, no_of_classes), dtype=np.float32)
        onehot_label[layer_idx, component_idx, trainId_label] = 1
        batch_onehot_labels[i] = onehot_label
        #batch_onehot_labels[i] = trainId_label

    batch_feed_dict = model.create_feed_dict(batch_imgs, early_drop_prob=0.0,
                late_drop_prob=0.0, training=False, onehot_labels_batch=batch_onehot_labels)

    batch_loss, logits = sess.run([model.loss, model.logits],
                feed_dict=batch_feed_dict)

    predictions = np.argmax(logits, axis=3)

    for i in range(batch_size):
        prediction = predictions[i]
        cv2.imwrite("pred_" + str(i) + ".png", prediction)

    val_loss = batch_loss
    return val_loss

def train_data_iterator(batch_size, session):
    """
    - DOES:
    """

    # load the training data from disk:
    train_trainId_label_paths = cPickle.load(open(data_dir + "train_trainId_label_paths.pkl"))
    train_img_paths = cPickle.load(open(data_dir + "train_img_paths.pkl"))

    # compute the number of batches needed to iterate through the training data:
    global no_of_batches
    no_of_train_imgs = len(train_img_paths)
    no_of_batches = int(no_of_train_imgs/batch_size)

    batch_pointer = 0
    for step in range(no_of_batche):
        # get and yield the next batch_size imgs and onehot labels from the training data:
        batch_imgs = np.zeros((batch_size, img_height, img_width, 3), dtype=np.float32)
        batch_onehot_labels = np.zeros((batch_size, img_height, img_width, no_of_classes), dtype=np.float32)
        #batch_onehot_labels = np.zeros((batch_size, img_height, img_width), dtype=np.int32)
        layer_idx = np.arange(img_height).reshape(img_height, 1)
        component_idx = np.tile(np.arange(img_width), (img_height, 1))
        for i in range(batch_size):
            # read the next img:
            img = cv2.imread(train_img_paths[(batch_pointer + i)], -1)
            batch_imgs[i] = img

            trainId_label = cv2.imread(train_trainId_label_paths[(batch_pointer + i)], -1)
            # onehot_label = tf.one_hot(indices=trainId_label, depth=no_of_classes)
            # onehot_label = sess.run(onehot_label) # (convert to numpy array)
            onehot_label = np.zeros((img_height, img_width, no_of_classes), dtype=np.float32)
            onehot_label[layer_idx, component_idx, trainId_label] = 1
            batch_onehot_labels[i] = onehot_label
            #batch_onehot_labels[i] = trainId_label
        batch_pointer += batch_size

        yield (batch_imgs, batch_onehot_labels)

no_of_epochs = 120
model_id = "1" # (change this to not overwrite all log data when you train the model)

model = ENet_model(model_id)

batch_size = model.batch_size

# create a saver for saving all model variables/parameters:
saver = tf.train.Saver(write_version=tf.train.SaverDef.V2)

# initialize all log data containers:
train_loss_per_epoch = []
val_loss_per_epoch = []

# initialize a list containing the 5 best val losses (is used to tell when it
# makes sense to save a model checkpoint):
best_epoch_losses = [1000, 1000, 1000, 1000, 1000]

with tf.Session() as sess:
    # initialize all variables/parameters:
    init = tf.global_variables_initializer()
    sess.run(init)

    for epoch in range(no_of_epochs):
        print "###########################"
        print "######## NEW EPOCH ########"
        print "###########################"
        print "epoch: %d/%d" % (epoch+1, no_of_epochs)

        # run an epoch and get all batch losses:
        batch_losses = []
        for step, (imgs, onehot_labels) in enumerate(train_data_iterator(batch_size, sess)):
            # create a feed dict containing the batch data:
            batch_feed_dict = model.create_feed_dict(imgs, early_drop_prob=0.01,
                        late_drop_prob=0.1, training=True, onehot_labels_batch=onehot_labels)

            # compute the batch loss and compute & apply all gradients w.r.t to
            # the batch loss (without model.train_op in the call, the network
            # would NOT train, we would only compute the batch loss):
            batch_loss, _ = sess.run([model.loss, model.train_op],
                        feed_dict=batch_feed_dict)
            batch_losses.append(batch_loss)

            print "step: %d/%d, training batch loss: %g" % (step+1, no_of_batches, batch_loss)

        # compute the train epoch loss:
        train_epoch_loss = np.mean(batch_losses)
        # save the train epoch loss:
        train_loss_per_epoch.append(train_epoch_loss)
        # save the train epoch losses to disk:
        cPickle.dump(train_loss_per_epoch, open("%strain_loss_per_epoch.pkl"
                    % model.model_dir, "w"))
        print "training loss: %g" % train_epoch_loss

        # run the model on the validation data:
        val_loss = evaluate_on_val(batch_size, sess)
        # save the val epoch loss:
        val_loss_per_epoch.append(val_loss)
        # save the val epoch losses to disk:
        cPickle.dump(val_loss_per_epoch, open("%sval_loss_per_epoch.pkl"\
                    % model.model_dir, "w"))
        print "validaion loss: %g" % val_loss

        if val_loss < max(best_epoch_losses): # (if top 5 performance on val:)
            # save the model weights to disk:
            checkpoint_path = (model.checkpoints_dir + "model_" +
                        model.model_id + "_epoch_" + str(epoch + 1) + ".ckpt")
            saver.save(sess, checkpoint_path)
            print "checkpoint saved in file: %s" % checkpoint_path

            # update the top 5 val losses:
            index = best_epoch_losses.index(max(best_epoch_losses))
            best_epoch_losses[index] = val_loss

        # plot the training loss vs epoch and save to disk:
        plt.figure(1)
        plt.plot(train_loss_per_epoch, "k^")
        plt.plot(train_loss_per_epoch, "k")
        plt.ylabel("loss")
        plt.xlabel("epoch")
        plt.title("training loss per epoch")
        plt.savefig("%strain_loss_per_epoch.png" % model.model_dir)
        plt.close(1)

        # plot the val loss vs epoch and save to disk:
        plt.figure(1)
        plt.plot(val_loss_per_epoch, "k^")
        plt.plot(val_loss_per_epoch, "k")
        plt.ylabel("loss")
        plt.xlabel("epoch")
        plt.title("validation loss per epoch")
        plt.savefig("%sval_loss_per_epoch.png" % model.model_dir)
        plt.close(1)
