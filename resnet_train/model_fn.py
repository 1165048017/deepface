import tensorflow as tf


def conv_block(input_tensor, filters, stage, block, mode, strides=(2, 2), bias=False):
    """Helper function for building the convolution block"""

    layer_name = 'conv' + str(stage) + '_' + str(block)
    l = tf.layers.conv2d(input_tensor, filters[0], 1, strides=strides, use_bias=bias,
                         name=layer_name + '_1x1_reduce')
    l = tf.layers.batch_normalization(l, axis=3, name=layer_name + '_1x1_reduce/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)
    l = tf.nn.relu(l)

    l = tf.layers.conv2d(l, filters[1], 3, padding='SAME', use_bias=bias, name=layer_name + '_3x3')
    l = tf.layers.batch_normalization(l, axis=3, name=layer_name + '_3x3/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)
    l = tf.nn.relu(l)

    l = tf.layers.conv2d(l, filters[2], 1, name=layer_name + '_1x1_increase')
    l = tf.layers.batch_normalization(l, axis=3, name=layer_name + '_1x1_increase/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)

    m = tf.layers.conv2d(input_tensor, filters[2], 1, strides=strides, use_bias=bias, name=layer_name + '_1x1_proj')
    m = tf.layers.batch_normalization(m, axis=3, name=layer_name + '_1x1_proj/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)

    l = tf.add(l, m)
    l = tf.nn.relu(l)
    return l


def identity_block(input_tensor, filters, stage, block, mode, bias=False):
    """Helper function for building the identity block"""

    layer_name = 'conv' + str(stage) + '_' + str(block)
    l = tf.layers.conv2d(input_tensor, filters[0], 1, use_bias=bias, name=layer_name + '_1x1_reduce')
    l = tf.layers.batch_normalization(l, axis=3, name=layer_name + '_1x1_reduce/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)
    l = tf.nn.relu(l)

    l = tf.layers.conv2d(l, filters[1], 3, padding='SAME', use_bias=bias, name=layer_name + '_3x3')
    l = tf.layers.batch_normalization(l, name=layer_name + '_3x3/bn', training=mode == tf.estimator.ModeKeys.TRAIN)
    l = tf.nn.relu(l)

    l = tf.layers.conv2d(l, filters[2], 1, use_bias=bias, name=layer_name + '_1x1_increase')
    l = tf.layers.batch_normalization(l, name=layer_name + '_1x1_increase/bn',
                                      training=mode == tf.estimator.ModeKeys.TRAIN)

    l = tf.add(l, input_tensor)
    l = tf.nn.relu(l)
    return l


def resnet_model_fn(features, labels, mode):
    """Model function for ResNet architecture"""
    input_layer = tf.reshape(features, [-1, 224, 224, 3])

    # Building hidden layers (ResNet architecture)
    # First block:
    l = tf.layers.conv2d(input_layer, 64, (7, 7), strides=(2, 2), padding='SAME', use_bias=False, name='conv1/7x7_s2')
    l = tf.layers.batch_normalization(l, axis=3, name='conv1/7x7_s2/bn', training=mode == tf.estimator.ModeKeys.TRAIN)
    l = tf.nn.relu(l)
    l = tf.layers.max_pooling2d(l, 3, 2)

    # Second block:
    l = conv_block(l, [64, 64, 256], stage=2, block=1, mode=mode, strides=(1, 1))
    l = identity_block(l, [64, 64, 256], stage=2, block=2, mode=mode)
    l = identity_block(l, [64, 64, 256], stage=2, block=3, mode=mode)

    # Third block:
    l = conv_block(l, [128, 128, 512], stage=3, block=1, mode=mode)
    l = identity_block(l, [128, 128, 512], stage=3, block=2, mode=mode)
    l = identity_block(l, [128, 128, 512], stage=3, block=3, mode=mode)
    l = identity_block(l, [128, 128, 512], stage=3, block=4, mode=mode)

    # Fourth block:
    l = conv_block(l, [256, 256, 1024], stage=4, block=1, mode=mode)
    l = identity_block(l, [256, 256, 1024], stage=4, block=2, mode=mode)
    l = identity_block(l, [256, 256, 1024], stage=4, block=3, mode=mode)
    l = identity_block(l, [256, 256, 1024], stage=4, block=4, mode=mode)
    l = identity_block(l, [256, 256, 1024], stage=4, block=5, mode=mode)
    l = identity_block(l, [256, 256, 1024], stage=4, block=6, mode=mode)

    # Fifth block:
    l = conv_block(l, [512, 512, 2048], stage=5, block=1, mode=mode)
    l = identity_block(l, [512, 512, 2048], stage=5, block=2, mode=mode)
    l = identity_block(l, [512, 512, 2048], stage=5, block=3, mode=mode)

    # Final stage:
    l = tf.layers.average_pooling2d(l, 7, 1)
    l = tf.layers.flatten(l)

    # Output layer
    logits = tf.layers.dense(l, units=8631)

    # Predictions
    predictions = {
        "classes": tf.argmax(logits, axis=1),
        "probabilities": tf.nn.softmax(logits, name='softmax_tensor')
    }

    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)

    # Calculate Loss
    loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=logits)

    # Configure the Training Op
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.GradientDescentOptimizer(learning_rate=0.001)
        train_op = optimizer.minimize(loss=loss, global_step=tf.train.get_global_step())
        tf.summary.scalar('my_accuracy', tf.metrics.accuracy(labels=labels,
                                                             predictions=predictions["classes"])[1])
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)

    # Add evaluation metrics
    eval_metric_ops = {
        "accuracy": tf.metrics.accuracy(labels=labels,
                                        predictions=predictions["classes"])
    }

    return tf.estimator.EstimatorSpec(mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)
