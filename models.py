# Defines the models used in the experiments

import numpy as np
from keras.layers import Dense, Input, merge, Activation, Dropout, RepeatVector
from keras.models import Model
from keras.layers.convolutional import Convolution1D
from keras.layers.recurrent import GRU
from keras.layers.normalization import BatchNormalization
from util import one_hot, NUM_STYLES
from music import NUM_CLASSES, NOTES_PER_BAR, NUM_KEYS
from keras.models import load_model

def gru_stack(time_steps, dropout=False, batch_norm=True, layers=[256, 256, 256, 256, 256]):
    note_input = Input(shape=(time_steps, NUM_CLASSES), name='note_input')

    # Context inputs
    beat_input = Input(shape=(time_steps, 2), name='beat_input')
    completion_input = Input(shape=(time_steps, 1), name='completion_input')
    style_input = Input(shape=(time_steps, NUM_STYLES), name='style_input')
    context = merge([completion_input, beat_input, style_input], mode='concat')

    x = note_input # Convolution1D(64, 3, border_mode='same')(note_input)

    # Create a distributerd representation of context
    context = GRU(64, return_sequences=True, name='context')(context)

    for i, num_units in enumerate(layers):
        y = x
        x = merge([x, context], mode='concat')

        x = GRU(
            num_units,
            return_sequences=i != len(layers) - 1,
            name='lstm' + str(i)
        )(x)

        # Residual connection
        if i > 0 and i < len(layers) - 1:
            x = merge([x, y], mode='sum')

        if batch_norm:
            x = BatchNormalization()(x)

        x = Activation('relu')(x)

        if dropout:
            x = Dropout(0.5)(x)

    return [note_input, beat_input, completion_input, style_input], x


def note_model(time_steps):
    inputs, x = gru_stack(time_steps, False)

    # Multi-label
    policy = Dense(NUM_CLASSES, name='policy', activation='softmax')(x)
    value = Dense(1, name='value', activation='linear')(x)

    model = Model(inputs, [policy, value])
    #model.load_weights('data/supervised.h5', by_name=True)
    # Create value output
    return model


def supervised_model(time_steps):
    inputs, x = gru_stack(time_steps)

    # Multi-label
    x = Dense(NUM_CLASSES, name='policy', activation='softmax')(x)

    model = Model(inputs, x)
    model.compile(optimizer='adam', loss='categorical_crossentropy',
                  metrics=['accuracy'])
    return model


def note_preprocess(env, x):
    note, beat = x
    return (one_hot(note, NUM_CLASSES), one_hot(beat, NOTES_PER_BAR))
