from toolICOrdict import *

class Batch(ICOrdict):
    
    # def reset(self):
    #     ### remove all elements while keeping the reference
    #     del self[:]
    
    def applyFunctTo(self, funct, ids, complement=False, check=None, changes= False):
        if complement:
            ids = self.getComplementKeys(ids)
        for i in ids:
            if check is None or self.applyFunct(check, i):
                self.applyFunct(funct, i)

    def applyFunct(self, funct, i, changes=False):
        result = None
        try:
            if type(funct) == str and len(funct) > 0:
                if funct == "identity":
                    result = self[i]
                elif funct[0]== ".":
                    result = eval("self.getElement(i)"+funct)
                else:
                    result = eval(funct)(self.getElement(i))
            elif callable(funct):
                result = funct(self.getElement(i))
        except TypeError:
            result = None
        else:
            if changes:
                self._isChanged = True
        return result

    def sortIds(self, ids, custom_parameters, new_ids=None):
        ### sort
        parameters = { "sort_funct": None,
                       "sort_reverse": False}
        parameters.update(custom_parameters)

        if callable(parameters["sort_funct"]) and len(ids) > 0:
            ids.sort(key=lambda x: parameters["sort_funct"](self.getElement(x)), reverse=parameters["sort_reverse"])
        return ids

    def filterLast(self, ids, custom_parameters):
        ### check last element against previous in list
        ### filters out if strictly more than filter_max elements
        ### that return a value strictly over thres are encountered
        ### returns True is element should be filtered out
        ### filter_thres is by default 0, for use with bool function (counting trues)
        ### filter_max should be >= 0
        ### There should be at least filter_max+2 elements in the list
        ### (compared element + filter_max comparisons + one comparison too many)
        ### otherwise the case is certainly acceptable
        parameters = { "filter_funct": None,
                       "filter_thres": 0,
                       "filter_max": 0}
        parameters.update(custom_parameters)

        if callable(parameters["filter_funct"]) and len(ids) >= parameters["filter_max"]+2:
            filter_out = 0
            posC = len(ids)-1
            posP = 0
            while filter_out <= parameters["filter_max"]  and posP < posC:
                filter_out += (parameters["filter_funct"](self.getElement(ids[posC]), self.getElement(ids[posP])) > parameters["filter_thres"]) 
                posP += 1
            return filter_out > parameters["filter_max"]
        return False

    def filtersingleIds(self, ids, custom_parameters, complement=False, new_ids=None):
        ### filters out if returned value is over thres
        ### filter_thres is by default 0, for use with bool function (filters trues out)
        parameters = { "filter_funct": None,
                       "filter_thres": 0}
        parameters.update(custom_parameters)

        if complement:
            if callable(parameters["filter_funct"]):
                return [i for i in ids if (( new_ids is not None and \
                                             ( i not in new_ids \
                                               or not parameters["filter_funct"](self.getElement(i)) <= parameters["filter_thres"]))
                                           or (new_ids is None and \
                                               not parameters["filter_funct"](self.getElement(i)) <= parameters["filter_thres"]))]
            else:
                return []
        else:
            if callable(parameters["filter_funct"]):
                return [i for i in ids if (( new_ids is not None and \
                                             ( i not in new_ids \
                                               or not parameters["filter_funct"](self.getElement(i)) > parameters["filter_thres"]))
                                           or (new_ids is None and \
                                               not parameters["filter_funct"](self.getElement(i)) > parameters["filter_thres"]))]
            else:
                return ids

    def filtertofirstIds(self, ids, custom_parameters, complement=False, new_ids=None):
        ### filter list checking elements against first in list
        parameters = { "filter_funct": None,
                       "filter_thres": 0}
        parameters.update(custom_parameters)

        comp_ids = []
        if callable(parameters["filter_funct"]) and len(ids) >= 2:
            ## start from where the condition might be broken
            posC = 0
            posP = 1
            while posP < len(ids):
                if (parameters["filter_funct"](self.getElement(ids[posP]), self.getElement(ids[posC])) > parameters["filter_thres"]):
                    comp_ids.append(ids.pop(posP))
                else:
                    posP += 1
        if complement:
            return comp_ids
        return ids
    
    def filterpairsIds(self, ids, custom_parameters, complement=False, new_ids=None):
        ### filter list checking elements against previous in list
        parameters = { "filter_funct": None,
                       "filter_thres": 0,
                       "filter_max": 0}
        parameters.update(custom_parameters)
        # if new_ids is not None:
        #     pdb.set_trace()
        #     print new_ids

        comp_ids = []
        if callable(parameters["filter_funct"]) and len(ids) >= parameters["filter_max"]+2:
            ## start from where the condition might be broken
            posC = parameters["filter_max"]+1
            # new_ahead = ids[:posC+1]
            if new_ids is None or parameters["filter_max"] > 1:
                while posC < len(ids):
                    if self.filterLast(ids[:posC+1], parameters):
                        comp_ids.append(ids.pop(posC))
                    else:
                        posC += 1
            else:
                idxs = sorted([(ids.index(i), i) for i in new_ids if i in ids])+[(len(ids), None)]
                ### pdb.set_trace()
                new_keep = []                
                off = 0
                for i in range(len(idxs)-1):
                    if self.filterLast(ids[:idxs[i][0]+1-off], parameters):
                        comp_ids.append(ids.pop(idxs[i][0]-off))
                        off += 1
                    else:
                        new_keep.append(idxs[i][1])

                    if len(new_keep) > 0:
                        j = idxs[i][0]+1
                        noff = 0
                        while j < idxs[i+1][0]:
                            if self.filterLast(new_keep+[ids[j-off-noff]], parameters):
                                ### pdb.set_trace()
                                comp_ids.append(ids.pop(j-off-noff))
                                noff += 1
                            # else:
                            j+= 1
                        off += noff
        if complement:
            return comp_ids
        return ids

    def cutIds(self, ids, custom_parameters, complement=False, new_ids=None):
        ### cutoff by number, (by value can be implemented in the filter functions)
        ### cutoff_direct: 0: strict, -1: floor cut back in case of equals, 1: round cut uphead in case of equals
        ### equal_funct: check for equals
        parameters = { "cutoff_nb": None,
                       "cutoff_direct": 0,
                       "equal_funct": None} 
        parameters.update(custom_parameters)

        cut = parameters["cutoff_nb"]
        if cut is not None and cut < len(ids):
            if parameters["cutoff_direct"] != 0 and callable(parameters["equal_funct"]):
                while cut > 0 and cut < len(ids) and \
                          self.applyFunct(parameters["equal_funct"], ids[cut-1]) == \
                          self.applyFunct(parameters["equal_funct"], ids[cut]):
                    cut += parameters["cutoff_direct"]
            if complement:
                del ids[:cut]
            else:
                del ids[cut:]
        return ids
    
    def selected(self, actions_parameters =[], ids=None, complement=False, new_ids=None):
        ### applies a sequence of action to select a sequence of elements from the batch
        if ids is None:
            ids = self.getIds()
        before_ids = list(ids)
        if len(self) > 0:
            for action, parameters in actions_parameters:
                method_string = 'self.%sIds' % action
                try:
                    method_compute =  eval(method_string)
                except AttributeError:
                    raise Exception('Oups action method does not exist (%s)!'  % action)
                ids = method_compute(ids, parameters, new_ids=new_ids)
                # if new_ids is not None:
                #     comp_ids = method_compute(ids, parameters)
                #     if ids != comp_ids:
                #         print "OUPS", method_string, ids, "vs.", comp_ids
        if complement:
            ids = (set(before_ids)-set(ids))
        return ids

    def selected_old(self, actions_parameters =[], ids=None, complement=False, new_ids=None):
        ### applies a sequence of action to select a sequence of elements from the batch
        if ids is None:
            ids = self.getIds()
        before_ids = list(ids)
        if len(self) > 0:
            ## pdb.set_trace()
            for action, parameters in actions_parameters:
                method_string = 'self.%sIds' % action
                try:
                    method_compute =  eval(method_string)
                except AttributeError:
                    raise Exception('Oups action method does not exist (%s)!'  % action)
                ids = method_compute(ids, parameters)
                print action, len(ids) 
        if complement:
            ids = (set(before_ids)-set(ids))
        return ids


    def __str__(self):
        return 'Batch with %i elements, isChanged = %s' % (len(self), self.isChanged)

