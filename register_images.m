% ir = imread("C:/data/FLIR_ADAS_1_3/train/thermal_8_bit/FLIR_04274.jpeg");
% rgb = imread("C:/data/FLIR_ADAS_1_3/train/RGB/FLIR_04274.jpg");
% 
% [mp, fp] = cpselect(rgb, ir, 'Wait', true);
% 
% t = fitgeotrans(mp, fp, 'projective');
% Rfixed = imref2d(size(ir));
% registered = imwarp(rgb, t, 'OutputView', Rfixed);
% 
% imshowpair(ir, registered, 'blend')

% save("parameters.mat", "mp", "fp");

myDirRGB = "C:/data/FLIR_ADAS_1_3/video/RGB/";
myFiles = dir(fullfile(myDirRGB, '*.jpg'));

myDirIR = "C:/data/FLIR_ADAS_1_3/video/thermal_8_bit/";
load("parameters.mat");

t = fitgeotrans(mp, fp, 'projective');
%gets all wav files in struct
for k = 1:length(myFiles)
 rgbFileName = myFiles(k).name;
 rgbFullFileName = fullfile(myDirRGB, rgbFileName);
 
 rgb = imread(rgbFullFileName);
 
 Rfixed = imref2d(size(ir));
 registered = imwarp(rgb, t, 'OutputView', Rfixed);
 
 imwrite(registered, strcat("C:/data/FLIR_ADAS_1_3/video/registered_rgb/", ...
                    strrep(rgbFileName, '.jpg', '.jpeg'))); 
end