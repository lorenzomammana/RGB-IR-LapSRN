import torch
import torch.nn as nn
import numpy as np
import math
from guided_filter import GuidedFilter2d


def get_upsample_filter(size):
    """Make a 2D bilinear kernel suitable for upsampling"""
    factor = (size + 1) // 2
    if size % 2 == 1:
        center = factor - 1
    else:
        center = factor - 0.5
    og = np.ogrid[:size, :size]
    filter = (1 - abs(og[0] - center) / factor) * \
             (1 - abs(og[1] - center) / factor)
    return torch.from_numpy(filter).float()


class RecursiveBlock(nn.Module):
    def __init__(self, d):
        super(RecursiveBlock, self).__init__()

        self.block = nn.Sequential()
        for i in range(d):
            self.block.add_module("relu_" + str(i), nn.LeakyReLU(0.2, inplace=True))

            self.block.add_module("conv_" + str(i), nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3,
                                                              stride=1, padding=1, bias=True))

    def forward(self, x):
        output = self.block(x)
        return output


class FeatureEmbedding(nn.Module):
    def __init__(self, r, d):
        super(FeatureEmbedding, self).__init__()

        self.recursive_block = RecursiveBlock(d)
        self.num_recursion = r

    def forward(self, x):
        output = x.clone()

        # The weights are shared within the recursive block!
        for i in range(self.num_recursion):
            output = self.recursive_block(output) + x

        return output


class LapSrnMS(nn.Module):
    def __init__(self, r, d, scale):
        super(LapSrnMS, self).__init__()

        self.scale = scale
        self.conv_input = nn.Conv2d(in_channels=3, out_channels=64, kernel_size=3, stride=1, padding=1, bias=True, )

        self.transpose = nn.PixelShuffle(2)

        self.conv_t_1 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=1, padding=1, bias=True, )
        self.relu_t_1 = nn.LeakyReLU(0.2)
        self.conv_t_2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1, bias=True, )
        self.relu_t_2 = nn.LeakyReLU(0.2)

        self.relu_features = nn.LeakyReLU(0.2, inplace=True)

        self.guided_filter = GuidedFilter2d(3, 1e-3)

        self.scale_img = nn.ConvTranspose2d(in_channels=1, out_channels=1, kernel_size=4,
                                            stride=2, padding=1, bias=False)

        self.predict = nn.Conv2d(in_channels=64, out_channels=1, kernel_size=3, stride=1, padding=1, bias=True)
        self.features = FeatureEmbedding(r, d)

        i_conv = 0
        i_tconv = 0

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                if i_conv == 0:
                    m.weight.data = 0.001 * torch.randn(m.weight.shape)
                else:
                    m.weight.data = math.sqrt(2 / (3 * 3 * 64)) * torch.randn(m.weight.shape)
                    # torch.nn.init.kaiming_uniform_(m.weight, a=0.2, nonlinearity='leaky_relu')

                i_conv += 1

                if m.bias is not None:
                    m.bias.data.zero_()
            if isinstance(m, nn.ConvTranspose2d):
                if i_tconv == 0:
                    m.weight.data = math.sqrt(2 / (3 * 3 * 64)) * torch.randn(m.weight.shape)
                else:
                    c1, c2, h, w = m.weight.data.size()
                    weight = get_upsample_filter(h)
                    m.weight.data = weight.view(1, 1, h, w).repeat(c1, c2, 1, 1)

                i_tconv += 1

                if m.bias is not None:
                    m.bias.data.zero_()

    def forward(self, x, x_ir):
        features = self.conv_input(x)
        output_images = []
        rescaled_img = x_ir.clone()

        for i in range(int(math.log2(self.scale))):
            features = self.features(features)
            features = self.transpose(self.relu_features(features))

            features = self.relu_t_1(self.conv_t_1(features))
            features = self.relu_t_2(self.conv_t_2(features))
            predict = self.predict(features)

            if i == 0:
                rescaled_img = self.guided_filter(x_ir, x)

            rescaled_img = self.scale_img(rescaled_img)

            out = torch.add(predict, rescaled_img)

            output_images.append(out)

        return output_images


class CharbonnierLoss(nn.Module):
    """L1 Charbonnierloss."""
    def __init__(self):
        super(CharbonnierLoss, self).__init__()
        self.eps = 1e-6

    def forward(self, X, Y):
        diff = torch.add(X, -Y)
        error = torch.sqrt(diff * diff + self.eps)
        # print(error)
        loss = torch.sum(error)
        return loss
