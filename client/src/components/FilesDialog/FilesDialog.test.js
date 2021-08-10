import FilesDialog from "./FilesDialog";
import SelectionDialog from "components/SelectionDialog/SelectionDialog";
import DataDialogTable from "components/SelectionDialog/DataDialogTable";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import {
    rootId,
    directoryId,
    subDirectoryId,
    subSubDirectoryId,
    rootResponse,
    pdbResponse,
    directory1RecursiveResponse,
    directory1Response,
    subsubdirectoryResponse,
} from "./testingData";
import { selectionStates } from "components/SelectionDialog/selectionStates";

jest.mock("app");

const api_paths_map = new Map([
    ["/api/remote_files/plugins", rootResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip", pdbResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1&recursive=true", directory1RecursiveResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1", directory1Response],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1/subdirectory1", subsubdirectoryResponse],
]);

// PLEASE NOTE
// during this test we assume this route tree:
// |-- directory1
// |   |-- directory1file1
// |   |-- directory1file2
// |   |-- directory1file3
// |   |-- subdirectory1
// |   |   `-- subsubdirectory
// |   |       `-- subsubfile
// |   `-- subdirectory2
// |       `-- subdirectory2file
// |-- directory2
// |   |-- directory2file1
// |   `-- directory2file2
// |-- file1
// |-- file2

describe("FilesDialog/FilesDialog.vue", () => {
    let wrapper;
    let axiosMock;
    let localVue;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        localVue = createLocalVue();

        wrapper = shallowMount(FilesDialog, {
            propsData: { multiple: true },
            localVue,
        });

        // register axios paths
        for (const [path, response] of api_paths_map.entries()) {
            axiosMock.onGet(path).reply(200, response);
        }

        await flushPromises();
    });

    it("should show the same number of items", async () => {
        await open_root_folder();
        assert_shown_items(pdbResponse.length);
    });

    it("select files", async () => {
        const applyForEachFile = (func) => {
            get_rendered_files().forEach((file) => {
                func(file);
            });
        };

        await open_root_folder();
        const files = pdbResponse.filter((item) => item.class === "File");

        expect(wrapper.vm.hasValue).toBe(false);

        // assert number of rendered files
        assert_shown_items(files.length, true);

        // select each rendered file
        applyForEachFile((file) => clickOn(file));

        await flushPromises();
        // assert the number of selected files
        expect(wrapper.vm.model.count()).toBe(files.length);

        // assert that re-rendered files are selected
        applyForEachFile((file) => {
            expect(file._rowVariant).toBe(selectionStates.selected);
            wrapper.vm.model.exists(file.id);
        });
        // assert that OK button is active
        expect(wrapper.vm.hasValue).toBe(true);

        //    unselect each file
        applyForEachFile((file) => clickOn(file));

        // assert that OK button is disables
        expect(wrapper.vm.hasValue).toBe(false);
    });

    it("select directory", async () => {
        await open_root_folder();

        // select directory
        await clickOn(getRenderedDirectory(directoryId));

        const [response_files, response_directories] = [[], []];

        // separate files and directories from response
        directory1RecursiveResponse.forEach((item) => {
            item.class === "File" ? response_files.push(item) : response_directories.push(item);
        });

        expect(wrapper.vm.model.count()).toBe(response_files.length);

        // +1 because we additionally selected the "directory1" dir
        expect(wrapper.vm.selectedDirectories.length).toBe(response_directories.length + 1);

        // go inside directory1
        await openDirectory(directoryId);

        // select icon button should be active
        expect(wrapper.vm.selectAllIcon).toBe(selectionStates.selected);

        //every item should be selected
        wrapper.vm.items.forEach((item) => {
            expect(item._rowVariant).toBe(selectionStates.selected);
            expect(
                item.isLeaf
                    ? wrapper.vm.model.exists(item.id)
                    : wrapper.vm.selectedDirectories.some(({ id }) => id === item.id)
            ).toBe(true);
        });

        const file = wrapper.vm.items.find((item) => item.isLeaf);

        // unlesect random file
        await clickOn(file);

        // go back
        wrapper.vm.load();
        await flushPromises();

        // ensure that it has "mixed" icon
        expect(getRenderedDirectory(directoryId)._rowVariant).toBe(selectionStates.mixed);
    });

    // Unselect subdirectory1
    it("unselect sub-directory", async () => {
        await open_root_folder();
        const table = getTable();
        // select directory1
        table.$emit("clicked", getRenderedDirectory(directoryId));
        await flushPromises();
        //go inside subDirectoryId
        await openDirectory(directoryId);
        await openDirectory(subDirectoryId);
        // unselect subfolder
        await clickOn(getRenderedDirectory(subSubDirectoryId));
        // directory should be unselected
        expect(getRenderedDirectory(subSubDirectoryId)._rowVariant).toBe(selectionStates.unselected);
        // selectAllIcon should be unselected
        expect(wrapper.vm.selectAllIcon).toBe(selectionStates.unselected);
        // go back
        wrapper.vm.load();
        // go back
        wrapper.vm.load();
        await flushPromises();
        expect(getRenderedDirectory(directoryId)._rowVariant).toBe(selectionStates.mixed);
    });

    /** Util methods **/
    const open_root_folder = async () => {
        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        assert_shown_items(rootResponse.length);

        // find desired rootElement
        const rootElement = wrapper.vm.items.find((item) => rootId === item.id);

        // open root folder with rootId
        await clickOn(rootElement);
    };
    const openDirectory = async (directoryId) => {
        getTable().$emit("open", getRenderedDirectory(directoryId));
        await flushPromises();
    };
    const clickOn = async (element) => {
        getTable().$emit("clicked", element);
        await flushPromises();
    };
    const getRenderedDirectory = (directoryId) => wrapper.vm.items.find(({ id }) => directoryId === id);

    const get_rendered_files = () => wrapper.vm.items.filter((item) => item.isLeaf);

    const getTable = () => wrapper.findComponent(DataDialogTable).vm;

    const assert_shown_items = (length, filesOnly) => {
        const shownItems = filesOnly ? get_rendered_files() : wrapper.vm.items;
        expect(shownItems.length).toBe(length);
    };
});
